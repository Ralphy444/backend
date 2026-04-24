from rest_framework import serializers
from .models import User
from decimal import Decimal, InvalidOperation


def clean_coordinate(value):
    """Accept any lat/lng value and return a safe rounded Decimal (6 decimal places)."""
    if value is None or value == '' or value == 'null':
        return None
    try:
        return round(Decimal(str(value)), 6)
    except (InvalidOperation, TypeError, ValueError):
        return None


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)
    user_type = serializers.ChoiceField(choices=[('customer', 'Customer'), ('delivery', 'Delivery Rider')], default='customer')
    username = serializers.CharField(max_length=150)
    latitude = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    longitude = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'phone', 'address', 'latitude', 'longitude', 'date_of_birth', 'user_type', 'motorcycle_color', 'plate_number', 'driver_license']
        extra_kwargs = {
            'phone': {'required': False},
            'address': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
            'latitude': {'required': False},
            'longitude': {'required': False},
            'date_of_birth': {'required': False},
            'user_type': {'required': False},
            'motorcycle_color': {'required': False},
            'plate_number': {'required': False},
            'driver_license': {'required': False},
        }

    def validate_username(self, value):
        # Allow special characters and uppercase — only check uniqueness
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('A user with that username already exists.')
        return value

    def create(self, validated_data):
        lat = clean_coordinate(validated_data.get('latitude'))
        lng = clean_coordinate(validated_data.get('longitude'))
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone', ''),
            address=validated_data.get('address', ''),
            latitude=lat,
            longitude=lng,
            date_of_birth=validated_data.get('date_of_birth', None),
            user_type=validated_data.get('user_type', 'customer'),
            motorcycle_color=validated_data.get('motorcycle_color', ''),
            plate_number=validated_data.get('plate_number', ''),
            driver_license=validated_data.get('driver_license', ''),
        )
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'address', 'latitude', 'longitude', 'date_of_birth', 'date_joined', 'user_type']
        read_only_fields = ['id', 'username', 'email', 'date_joined', 'user_type']
