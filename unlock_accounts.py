import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from accounts.models import User

print("Unlocking all user accounts...\n")
print("="*80)

all_users = User.objects.all()

for user in all_users:
    user.failed_login_attempts = 0
    user.account_locked_until = None
    user.save()
    print(f"Unlocked: {user.username}")

print("="*80)
print(f"\nAll {all_users.count()} accounts unlocked and ready to login!")
