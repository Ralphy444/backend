import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from accounts.models import User

username = 'delivery'
password = 'delivery123'
email = 'delivery@example.com'

# Delete existing delivery user if exists
User.objects.filter(username=username).delete()

# Create delivery rider
user = User.objects.create_user(
    username=username,
    email=email,
    password=password,
    user_type='delivery',
    first_name='Delivery',
    last_name='Rider',
    phone='09123456789'
)

print("=" * 50)
print("Delivery Rider Account Created!")
print("=" * 50)
print(f"Username: {username}")
print(f"Password: {password}")
print(f"User Type: delivery")
print("=" * 50)
print("Login at:")
print("- Django Admin: http://localhost:8000/admin/")
print("- Mobile App: Use same credentials")
print("=" * 50)
