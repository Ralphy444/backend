import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from stores.models import Store, MenuItem
from accounts.models import User

# Create store admins
stores_data = [
    {'name': 'McDonald\'s', 'category': 'Burgers', 'emoji': '🍔', 'delivery_time': '20-30 min', 'username': 'mcdonalds_admin'},
    {'name': 'Pizza Hut', 'category': 'Pizza', 'emoji': '🍕', 'delivery_time': '25-35 min', 'username': 'pizzahut_admin'},
    {'name': 'KFC', 'category': 'Chicken', 'emoji': '🍗', 'delivery_time': '15-25 min', 'username': 'kfc_admin'},
    {'name': 'Starbucks', 'category': 'Coffee & Drinks', 'emoji': '☕', 'delivery_time': '10-20 min', 'username': 'starbucks_admin'},
    {'name': 'Subway', 'category': 'Sandwiches', 'emoji': '🥪', 'delivery_time': '20-30 min', 'username': 'subway_admin'},
]

for store_data in stores_data:
    # Create admin user for store
    username = store_data['username']
    if not User.objects.filter(username=username).exists():
        admin_user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password='admin123',
            is_staff=True
        )
        print(f"Created admin: {username} / password: admin123")
    else:
        admin_user = User.objects.get(username=username)
    
    # Create store
    if not Store.objects.filter(name=store_data['name']).exists():
        store = Store.objects.create(
            name=store_data['name'],
            category=store_data['category'],
            emoji=store_data['emoji'],
            delivery_time=store_data['delivery_time'],
            admin=admin_user
        )
        print(f"Created store: {store.name}")

print("\nAll stores created! Each store has an admin account.")
print("Login to http://localhost:8000/admin with:")
print("- mcdonalds_admin / admin123")
print("- pizzahut_admin / admin123")
print("- kfc_admin / admin123")
print("- starbucks_admin / admin123")
print("- subway_admin / admin123")
