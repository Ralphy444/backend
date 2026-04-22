from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import User
from .serializers import RegisterSerializer, UserSerializer
from stores.models import Restaurant

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        # Check for duplicate phone or plate number for delivery riders
        user_type = request.data.get('user_type', 'customer')
        if user_type == 'delivery':
            phone = request.data.get('phone', '').strip()
            plate = request.data.get('plate_number', '').strip()
            if phone and User.objects.filter(user_type='delivery', phone=phone).exists():
                return Response({'error': 'A rider with this phone number already exists.'}, status=status.HTTP_400_BAD_REQUEST)
            if plate and User.objects.filter(user_type='delivery', plate_number__iexact=plate).exists():
                return Response({'error': 'A rider with this plate number already exists.'}, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        # Save lat/lng manually since they come as strings from FormData
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        if lat and lng:
            try:
                user.latitude = float(lat)
                user.longitude = float(lng)
                user.save(update_fields=['latitude', 'longitude'])
            except (ValueError, TypeError):
                pass
        # Delivery riders need admin approval before they can login
        if user.user_type == 'delivery':
            user.is_active = False
            user.save()
        if 'motorcycle_photo' in request.FILES:
            user.motorcycle_photo = request.FILES['motorcycle_photo']
            user.save()
        if 'license_photo' in request.FILES:
            user.license_photo = request.FILES['license_photo']
            user.save()
        if 'face_left' in request.FILES:
            user.face_left = request.FILES['face_left']
            user.save()
        if 'face_front' in request.FILES:
            user.face_front = request.FILES['face_front']
            user.save()
        if 'face_right' in request.FILES:
            user.face_right = request.FILES['face_right']
            user.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': {
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': user.phone,
                'address': user.address,
                'user_type': user.user_type
            },
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
        if not user_obj.is_active:
            return Response({'error': 'Your account is inactive. Contact administrator.'}, status=status.HTTP_401_UNAUTHORIZED)
    except User.DoesNotExist:
        return Response({'error': 'Your username or password is incorrect'}, status=status.HTTP_401_UNAUTHORIZED)

    user = authenticate(username=username, password=password)

    if user:
        user.reset_failed_login()
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
