import os
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from accounts.models import User
from accounts.admin import UserAdmin
from django.contrib.admin.sites import site

print("=" * 50)
print("Testing User Model and Admin")
print("=" * 50)

try:
    # Test model
    print("\n1. Testing User Model...")
    users = User.objects.all()
    print(f"   Total users: {users.count()}")
    
    if users.exists():
        user = users.first()
        print(f"   Sample user: {user.username}")
        print(f"   First name: {user.first_name}")
        print(f"   Last name: {user.last_name}")
        print(f"   Email: {user.email}")
        print(f"   Phone: {user.phone}")
        print(f"   Address: {user.address}")
        print(f"   Latitude: {user.latitude}")
        print(f"   Longitude: {user.longitude}")
    
    # Test admin
    print("\n2. Testing Admin Configuration...")
    admin_instance = UserAdmin(User, site)
    print(f"   List display: {admin_instance.list_display}")
    print(f"   List filter: {admin_instance.list_filter}")
    print(f"   Search fields: {admin_instance.search_fields}")
    
    print("\n✅ All tests passed!")
    
except Exception as e:
    print("\n❌ ERROR FOUND:")
    print(f"   {type(e).__name__}: {str(e)}")
    print("\nFull traceback:")
    traceback.print_exc()

print("=" * 50)
