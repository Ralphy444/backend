from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.core.cache import cache
from django.conf import settings
from .models import User
from .serializers import RegisterSerializer, UserSerializer
from stores.models import Restaurant
import random
import json


def generate_otp():
    return str(random.randint(100000, 999999))


def send_otp_email(email, otp, name=''):
    """Send OTP via Brevo API — returns (success: bool, error_msg: str)."""
    try:
        result = send_mail(
            subject='\U0001f510 Your OrderBites Verification Code',
            message=(
                f'Hi {name or "there"},\n\n'
                f'Your email verification code is:\n\n'
                f'        {otp}\n\n'
                f'This code expires in 10 minutes.\n'
                f'Do not share this code with anyone.\n\n'
                f'\u2014 OrderBites Team'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        if result == 0:
            return (False, 'Email backend returned 0 (not sent). Check BREVO_API_KEY in environment variables.')
        return (True, '')
    except Exception as e:
        error_msg = f'{type(e).__name__}: {str(e)}'
        print(f'[OTP EMAIL ERROR] {error_msg}')
        return (False, error_msg)


def send_welcome_email(user):
    if not user.email:
        return
    try:
        if user.user_type == 'delivery':
            subject = '\U0001f6f5 Rider Application Received \u2014 Pending Approval'
            message = (
                f'Hi {user.first_name or user.username},\n\n'
                f'Thank you for registering as a delivery rider on OrderBites!\n\n'
                f'Your application is under review. We will notify you once approved.\n\n'
                f'\u2014 OrderBites Team'
            )
        else:
            subject = '\U0001f389 Welcome to OrderBites!'
            message = (
                f'Hi {user.first_name or user.username},\n\n'
                f'Your account has been verified and activated!\n\n'
                f'You can now start ordering your favorite food.\n\n'
                f'\u2014 OrderBites Team'
            )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception:
        pass


def send_login_notification(user):
    if not user.email:
        return
    try:
        from django.utils import timezone
        now = timezone.localtime(timezone.now()).strftime('%B %d, %Y at %I:%M %p')
        send_mail(
            subject='\U0001f510 New Login to Your OrderBites Account',
            message=(
                f'Hi {user.first_name or user.username},\n\n'
                f'A new login was detected on your account.\n'
                f'Time: {now} (Manila Time)\n\n'
                f'If this was not you, change your password immediately.\n\n'
                f'\u2014 OrderBites Team'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception:
        pass


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Step 1: Validate data, send OTP, store pending data in cache.
    User is NOT saved to DB yet.
    """
    user_type = request.data.get('user_type', 'customer')

    # Validate via serializer (does NOT save)
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data.get('email', '')
    username = serializer.validated_data.get('username', '')

    # Check duplicates
    if User.objects.filter(username__iexact=username).exists():
        return Response({'error': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)
    if email and User.objects.filter(email__iexact=email).exists():
        return Response({'error': 'Email already registered.'}, status=status.HTTP_400_BAD_REQUEST)

    if user_type == 'delivery':
        phone = request.data.get('phone', '').strip()
        plate = request.data.get('plate_number', '').strip()
        if phone and User.objects.filter(user_type='delivery', phone=phone).exists():
            return Response({'error': 'A rider with this phone number already exists.'}, status=status.HTTP_400_BAD_REQUEST)
        if plate and User.objects.filter(user_type='delivery', plate_number__iexact=plate).exists():
            return Response({'error': 'A rider with this plate number already exists.'}, status=status.HTTP_400_BAD_REQUEST)

    # For delivery riders — save immediately (needs admin approval anyway)
    if user_type == 'delivery':
        user = serializer.save()
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        if lat and lng:
            try:
                from decimal import Decimal
                user.latitude = round(Decimal(str(lat)), 6)
                user.longitude = round(Decimal(str(lng)), 6)
            except Exception:
                pass
        user.is_active = False
        user.is_email_verified = True
        user.save()
        for field in ['motorcycle_photo', 'license_photo', 'face_left', 'face_front', 'face_right']:
            if field in request.FILES:
                setattr(user, field, request.FILES[field])
        user.save()
        send_welcome_email(user)
        return Response({
            'message': 'Rider application submitted! Please wait for admin approval.',
        }, status=status.HTTP_201_CREATED)

    # For customers — store data in cache, send OTP, do NOT save to DB yet
    otp = generate_otp()
    cache_key = f'pending_reg_{username}'
    cache_data = {
        'otp': otp,
        'validated_data': {
            'username': username,
            'email': email,
            'password': request.data.get('password', ''),
            'first_name': serializer.validated_data.get('first_name', ''),
            'last_name': serializer.validated_data.get('last_name', ''),
            'phone': serializer.validated_data.get('phone', ''),
            'address': serializer.validated_data.get('address', ''),
            'latitude': request.data.get('latitude', ''),
            'longitude': request.data.get('longitude', ''),
            'user_type': 'customer',
        }
    }
    # Store in cache for 15 minutes
    cache.set(cache_key, json.dumps(cache_data), timeout=900)

    # Send OTP email
    name = serializer.validated_data.get('first_name', '') or username
    sent, err = send_otp_email(email, otp, name)
    if not sent:
        cache.delete(cache_key)
        return Response(
            {'error': f'Failed to send verification email: {err}. Please contact support.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response({
        'message': f'Verification code sent to {email}. Please check your inbox.',
        'email': email,
        'username': username,
        'requires_otp': True,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    """
    Step 2: Verify OTP, then create user in DB.
    """
    username = request.data.get('username', '').strip()
    otp_input = request.data.get('otp', '').strip()

    if not username or not otp_input:
        return Response({'error': 'Username and OTP are required.'}, status=status.HTTP_400_BAD_REQUEST)

    cache_key = f'pending_reg_{username}'
    cached = cache.get(cache_key)

    if not cached:
        return Response(
            {'error': 'OTP expired or not found. Please register again.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    data = json.loads(cached)

    if data['otp'] != otp_input:
        return Response({'error': 'Invalid OTP. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)

    # OTP correct — now create user in DB
    vd = data['validated_data']
    try:
        user = User.objects.create_user(
            username=vd['username'],
            email=vd['email'],
            password=vd['password'],
            first_name=vd.get('first_name', ''),
            last_name=vd.get('last_name', ''),
            phone=vd.get('phone', ''),
            address=vd.get('address', ''),
            user_type='customer',
            is_active=True,
            is_email_verified=True,
        )
        # Save coordinates if present
        lat = vd.get('latitude')
        lng = vd.get('longitude')
        if lat and lng:
            try:
                from decimal import Decimal
                user.latitude = round(Decimal(str(lat)), 6)
                user.longitude = round(Decimal(str(lng)), 6)
                user.save(update_fields=['latitude', 'longitude'])
            except Exception:
                pass
    except Exception as e:
        return Response({'error': f'Account creation failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Clear cache
    cache.delete(cache_key)

    # Send welcome email
    send_welcome_email(user)

    refresh = RefreshToken.for_user(user)
    return Response({
        'message': 'Email verified! Welcome to OrderBites \U0001f389',
        'user': {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'user_type': user.user_type,
        },
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_otp(request):
    username = request.data.get('username', '').strip()
    if not username:
        return Response({'error': 'Username is required.'}, status=status.HTTP_400_BAD_REQUEST)

    cache_key = f'pending_reg_{username}'
    cached = cache.get(cache_key)
    if not cached:
        return Response(
            {'error': 'Registration session expired. Please register again.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    data = json.loads(cached)
    new_otp = generate_otp()
    data['otp'] = new_otp
    cache.set(cache_key, json.dumps(data), timeout=900)

    email = data['validated_data']['email']
    name = data['validated_data'].get('first_name', '') or username
    sent, err = send_otp_email(email, new_otp, name)
    if not sent:
        return Response({'error': f'Failed to resend OTP: {err}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({'message': f'New verification code sent to {email}.'})

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()

    if not username or not password:
        return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user_obj = User.objects.get(username=username)
        if user_obj.is_account_locked():
            return Response({'error': 'Account is locked. Try again later.'}, status=status.HTTP_401_UNAUTHORIZED)
        if not user_obj.is_active and user_obj.user_type == 'delivery':
            return Response({'error': 'Your account is pending approval. Please wait for admin review.'}, status=status.HTTP_401_UNAUTHORIZED)
        if not user_obj.is_active and not user_obj.is_email_verified:
            return Response({
                'error': 'Please verify your email first.',
                'requires_otp': True,
                'username': user_obj.username,
                'email': user_obj.email,
            }, status=status.HTTP_401_UNAUTHORIZED)
        if not user_obj.is_active:
            return Response({'error': 'Your account is inactive. Contact administrator.'}, status=status.HTTP_401_UNAUTHORIZED)
    except User.DoesNotExist:
        return Response({'error': 'Your username or password is incorrect'}, status=status.HTTP_401_UNAUTHORIZED)

    user = authenticate(username=username, password=password)

    if user:
        user.reset_failed_login()
        # Send login notification email
        send_login_notification(user)
        refresh = RefreshToken.for_user(user)
        response_data = {
            'user': {
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': user.phone,
                'address': user.address,
                'is_staff': user.is_staff,
                'user_type': user.user_type
            },
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        if user.user_type == 'store_admin' or user.is_staff:
            try:
                restaurant = Restaurant.objects.get(admin=user)
                response_data['store'] = {
                    'id': restaurant.id,
                    'name': restaurant.name,
                    'category': restaurant.category,
                }
            except Restaurant.DoesNotExist:
                pass

        return Response(response_data)

    user_obj.increment_failed_login()
    return Response({'error': 'Your username or password is incorrect'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_store_admin(request):
    if not request.user.is_staff:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email', '')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    if not username or not password:
        return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
    user = User.objects.create_user(
        username=username,
        password=password,
        email=email,
        first_name=first_name,
        last_name=last_name,
        user_type='store_admin',
    )
    return Response({'id': user.id, 'username': user.username, 'message': 'Store admin created successfully'}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_push_token(request):
    token = request.data.get('push_token', '').strip()
    if token:
        request.user.push_token = token
        request.user.save(update_fields=['push_token'])
    return Response({'status': 'ok'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
