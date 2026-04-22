import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from accounts.models import User

username = 'admin'
email = 'admin@example.com'
password = 'admin123'

# Delete existing admin if exists
User.objects.filter(username=username).delete()

# Create new admin
user = User.objects.create_superuser(username=username, email=email, password=password)
print("=" * 50)
print("Admin account created successfully!")
print("=" * 50)
print(f"Username: {username}")
print(f"Password: {password}")
print(f"Email: {email}")
print("=" * 50)
print("Login at: http://localhost:8000/admin/")
print("=" * 50)
