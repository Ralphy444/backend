import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from accounts.models import User

print("\n" + "="*80)
print("ALL USERS IN THE SYSTEM")
print("="*80 + "\n")

# Get all users
all_users = User.objects.all().order_by('user_type', 'username')

if not all_users.exists():
    print("No users found in the database.")
else:
    # Group by user type
    customers = all_users.filter(user_type='customer')
    store_admins = all_users.filter(user_type='store_admin')
    delivery_riders = all_users.filter(user_type='delivery')
    
    print(f"TOTAL USERS: {all_users.count()}\n")
    
    if customers.exists():
        print("CUSTOMERS:")
        print("-" * 80)
        for user in customers:
            print(f"  Username: {user.username}")
            print(f"  Email: {user.email}")
            print(f"  Name: {user.first_name} {user.last_name}")
            print(f"  Phone: {user.phone or 'N/A'}")
            print(f"  Address: {user.address or 'N/A'}")
            print(f"  Password: Cannot retrieve (hashed in database)")
            print(f"  Tip: Check your registration code/script for password")
            print()
    
    if store_admins.exists():
        print("\nSTORE ADMINS:")
        print("-" * 80)
        for user in store_admins:
            print(f"  Username: {user.username}")
            print(f"  Email: {user.email}")
            print(f"  Name: {user.first_name} {user.last_name}")
            print(f"  Password: Cannot retrieve (hashed in database)")
            print()
    
    if delivery_riders.exists():
        print("\nDELIVERY RIDERS:")
        print("-" * 80)
        for user in delivery_riders:
            print(f"  Username: {user.username}")
            print(f"  Email: {user.email}")
            print(f"  Name: {user.first_name} {user.last_name}")
            print(f"  Motorcycle: {user.motorcycle_color or 'N/A'}")
            print(f"  Plate: {user.plate_number or 'N/A'}")
            print(f"  License: {user.driver_license or 'N/A'}")
            print(f"  Password: Cannot retrieve (hashed in database)")
            print()

print("\n" + "="*80)
print("KNOWN PASSWORDS FROM SCRIPTS:")
print("="*80)
print("  Delivery Riders: rider1/rider123, rider2/rider123")
print("  Check these files for other user passwords:")
print("    - create_admin.py")
print("    - create_delivery.py")
print("    - create_stores.py")
print("    - Any custom registration scripts you created")
print("="*80 + "\n")
