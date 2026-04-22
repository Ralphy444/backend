import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from accounts.models import User

password = 'rapica123'
all_users = User.objects.all()

print("Resetting all user passwords to: rapica123\n")
print("="*80)

for user in all_users:
    user.set_password(password)
    user.failed_login_attempts = 0
    user.account_locked_until = None
    user.save()
    print(f"Updated: {user.username} -> password: rapica123")

print("="*80)
print(f"\nAll {all_users.count()} users now have password: rapica123")
print("\nYou can now login with any username and password: rapica123")
