import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from accounts.models import User

print("=" * 60)
print("ALL USERS IN DATABASE")
print("=" * 60)

users = User.objects.all()
for user in users:
    print(f"\nUsername: {user.username}")
    print(f"Email: {user.email}")
    print(f"Is Staff: {user.is_staff}")
    print(f"Is Superuser: {user.is_superuser}")
    
    # Reset password to admin123
    user.set_password('admin123')
    user.save()
    print(f"✅ Password reset to: admin123")

print("\n" + "=" * 60)
print("ALL PASSWORDS RESET TO: admin123")
print("=" * 60)
