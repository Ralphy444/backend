import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import authenticate
from accounts.models import User

print("\n" + "="*80)
print("TESTING LOGIN FOR ALL USERS")
print("="*80 + "\n")

test_users = ['hanz', 'ralphy', 'rasta', 'admin', 'rider1', 'rider2', 'mcdonalds_admin']

for username in test_users:
    print(f"Testing: {username}")
    
    # Check if user exists
    try:
        user = User.objects.get(username=username)
        print(f"  User exists: YES")
        print(f"  Email: {user.email}")
        print(f"  Is Active: {user.is_active}")
        print(f"  Is Locked: {user.is_account_locked()}")
        print(f"  User Type: {user.user_type}")
        
        # Test authentication
        auth_user = authenticate(username=username, password='rapica123')
        if auth_user:
            print(f"  Authentication: SUCCESS")
        else:
            print(f"  Authentication: FAILED - Resetting password...")
            user.set_password('rapica123')
            user.failed_login_attempts = 0
            user.account_locked_until = None
            user.is_active = True
            user.save()
            
            # Test again
            auth_user = authenticate(username=username, password='rapica123')
            if auth_user:
                print(f"  Authentication after reset: SUCCESS")
            else:
                print(f"  Authentication after reset: STILL FAILED")
    except User.DoesNotExist:
        print(f"  User exists: NO")
    
    print()

print("="*80)
print("Testing complete!")
print("="*80)
