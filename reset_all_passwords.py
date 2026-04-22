import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from accounts.models import User

password = 'admin123'
all_users = User.objects.all()

print("Resetting all user passwords to: admin123\n")
print("="*80)

for user in all_users:
    user.set_password(password)
    user.save()
    print(f"Updated: {user.username} -> password: admin123")

print("="*80)
print(f"\nAll {all_users.count()} users now have password: admin123")
