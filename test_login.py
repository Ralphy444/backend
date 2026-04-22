import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import authenticate
from accounts.models import User

print("Testing login for all users with password: admin123\n")
print("="*80)

test_users = ['hanz', 'ralphy', 'rasta', 'admin', 'rider1', 'rider2']

for username in test_users:
    user = authenticate(username=username, password='admin123')
    if user:
        print(f"SUCCESS: {username} can login")
    else:
        print(f"FAILED: {username} cannot login")
        try:
            db_user = User.objects.get(username=username)
            print(f"  User exists. Resetting password...")
            db_user.set_password('admin123')
            db_user.save()
            user = authenticate(username=username, password='admin123')
            if user:
                print(f"  Fixed! {username} can now login")
            else:
                print(f"  Still failed for {username}")
        except User.DoesNotExist:
            print(f"  User {username} does not exist")

print("="*80)
print("\nAll users should now be able to login with: admin123")
