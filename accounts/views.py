from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
from .models import User
from .serializers import RegisterSerializer, UserSerializer
from stores.models import Restaurant


def send_otp_email(user, otp):
    try:
        send_mail(
            subject='🔐 Your OrderBites Verification Code',
            message=(
                f'Hi {user.first_name or user.username},\n\n'
                f'Your email verification code is:\n\n'
                f'  {otp}\n\n'
                f'This code expires in 10 minutes.\n'
                f'Do not share this code with anyone.\n\n'
                f'— OrderBites Team'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f'OTP email error: {e}')


def send_welcome_email(user):
    if not user.email:
        return
    try:
        if user.user_type == 'delivery':
            subject = '🛵 Rider Registration Received — Pending Approval'
            message = (
                f'Hi {user.first_name or user.username},\n\n'
                f'Thank you for registering as a delivery rider on OrderBites!\n\n'
                f'Your account is currently under review. You will receive another email once approved.\n\n'
                f'— OrderBites Team'
            )
        else:
            subject = '🎉 Welcome to OrderBites!'
            message = (
                f'Hi {user.first_name or user.username},\n\n'
                f'Welcome to OrderBites! Your account has been verified and activated.\n\n'
                f'You can now start ordering your favorite food!\n\n'
                f'— OrderBites Team'
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
            subject='🔐 New Login to Your OrderBites Account',
            message=(
                f'Hi {user.first_name or user.username},\n\n'
                f'A new login was detected on your OrderBites account.\n\n'
                f'  Time: {now} (Manila Time)\n\n'
                f'If this was not you, please change your password immediately.\n\n'
                f'— OrderBites Team'
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
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user_type = request.data.get('user_type', 'customer')
        if user_type == 'delivery':
            phone = request.data.get('phone', '').strip()
            plate = request.data.get('plate_number', '').strip()
            if phone and User.objects.filter(user_type='delivery', phone=phone).exists():
                return Response({'error': 'A rider with this phone number already exists.'}, status=status.HTTP_400_BAD_REQUEST)
            if plate and User.objects.filter(user_type='delivery', plate_number__iexact=plate).exists():
                return Response({'error': 'A rider with this plate number already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()

        # Save lat/lng
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        if lat and lng:
            try:
                from decimal import Decimal
                user.latitude = round(Decimal(str(lat)), 6)
                user.longitude = round(Decimal(str(lng)), 6)
                user.save(update_fields=['latitude', 'longitude'])
            except Exception:
                pass

        # Save photos
        for field in ['motorcycle_photo', 'license_photo', 'face_left', 'face_front', 'face_right']:
            if field in request.FILES:
                setattr(user, field, request.FILES[field])
        user.save()

        # Delivery riders — inactive until admin approves, send pending email
        if user.user_type == 'delivery':
            user.is_active = False
            user.is_email_verified = True  # no OTP needed for riders
            user.save()
            send_welcome_email(user)
            return Response({'message': 'Rider application submitted. Pending admin approval.'}, status=status.HTTP_201_CREATED)

        # Customer — inactive until OTP verified, send OTP
        user.is_active = False
        user.is_email_verified = False
        user.save()
        otp = user.generate_otp()
        send_otp_email(user, otp)

        return Response({
            'message': 'Registration successful! Please check your email for the verification code.',
            'email': user.email,
            'username': user.username,
            'requires_otp': True,
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    username = request.data.get('username', '').strip()
    otp = request.data.get('otp', '').strip()

    if not username or not otp:
        return Response({'error': 'Username and OTP are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

    if user.is_email_verified:
        return Response({'error': 'Email already verified. Please login.'}, status=status.HTTP_400_BAD_REQUEST)

    if not user.verify_otp(otp):
        return Response({'error': 'Invalid or expired OTP. Please request a new code.'}, status=status.HTTP_400_BAD_REQUEST)

    # Activate account
    user.is_active = True
    user.is_email_verified = True
    user.otp_code = ''
    user.otp_expires_at = None
    user.save()

    send_welcome_email(user)

    refresh = RefreshToken.for_user(user)
    return Response({
        'message': 'Email verified! Welcome to OrderBites 🎉',
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
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
    if user.is_email_verified:
        return Response({'error': 'Email already verified.'}, status=status.HTTP_400_BAD_REQUEST)
    otp = user.generate_otp()
    send_otp_email(user, otp)
    return Response({'message': f'New OTP sent to {user.email}'})

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
