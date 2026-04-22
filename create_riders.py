import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from accounts.models import User

# Create sample delivery riders
riders_data = [
    {
        'username': 'rider1',
        'email': 'rider1@example.com',
        'password': 'rider123',
        'first_name': 'Juan',
        'last_name': 'Dela Cruz',
        'phone': '09171234567',
        'motorcycle_color': 'Red Honda TMX',
        'plate_number': 'ABC-1234',
        'driver_license': 'N01-90-123456',
        'user_type': 'delivery'
    },
    {
        'username': 'rider2',
        'email': 'rider2@example.com',
        'password': 'rider123',
        'first_name': 'Pedro',
        'last_name': 'Santos',
        'phone': '09181234567',
        'motorcycle_color': 'Blue Yamaha Mio',
        'plate_number': 'XYZ-5678',
        'driver_license': 'N01-91-234567',
        'user_type': 'delivery'
    }
]

for rider_data in riders_data:
    username = rider_data['username']
    if User.objects.filter(username=username).exists():
        print(f"Rider {username} already exists. Updating...")
        rider = User.objects.get(username=username)
        rider.first_name = rider_data['first_name']
        rider.last_name = rider_data['last_name']
        rider.phone = rider_data['phone']
        rider.motorcycle_color = rider_data['motorcycle_color']
        rider.plate_number = rider_data['plate_number']
        rider.driver_license = rider_data['driver_license']
        rider.user_type = 'delivery'
        rider.save()
        print(f"Updated: {rider.first_name} {rider.last_name}")
    else:
        rider = User.objects.create_user(
            username=rider_data['username'],
            email=rider_data['email'],
            password=rider_data['password'],
            first_name=rider_data['first_name'],
            last_name=rider_data['last_name'],
            phone=rider_data['phone'],
            motorcycle_color=rider_data['motorcycle_color'],
            plate_number=rider_data['plate_number'],
            driver_license=rider_data['driver_license'],
            user_type=rider_data['user_type']
        )
        print(f"Created: {rider.first_name} {rider.last_name}")

print("\nDelivery riders setup complete!")
print("\nLogin credentials:")
print("Username: rider1, Password: rider123")
print("Username: rider2, Password: rider123")
