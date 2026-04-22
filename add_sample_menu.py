import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from stores.models import Store, MenuItem

# Sample menu items for each store
menu_data = {
    "McDonald's": [
        {'name': 'Big Mac', 'category': 'burger', 'description': 'Two beef patties, special sauce, lettuce, cheese', 'price': 150.00},
        {'name': 'McChicken', 'category': 'chicken', 'description': 'Crispy chicken fillet with mayo', 'price': 120.00},
        {'name': 'French Fries', 'category': 'fries', 'description': 'Golden crispy fries', 'price': 60.00},
        {'name': 'Coke', 'category': 'drinks', 'description': 'Refreshing Coca-Cola', 'price': 50.00},
        {'name': 'McFlurry', 'category': 'dessert', 'description': 'Soft serve ice cream with toppings', 'price': 80.00},
    ],
    "Pizza Hut": [
        {'name': 'Pepperoni Pizza', 'category': 'pizza', 'description': 'Classic pepperoni with mozzarella', 'price': 350.00},
        {'name': 'Hawaiian Pizza', 'category': 'pizza', 'description': 'Ham and pineapple', 'price': 320.00},
        {'name': 'Chicken Wings', 'category': 'chicken', 'description': 'Spicy buffalo wings', 'price': 180.00},
        {'name': 'Garlic Bread', 'category': 'other', 'description': 'Toasted bread with garlic butter', 'price': 90.00},
        {'name': 'Pepsi', 'category': 'drinks', 'description': 'Ice cold Pepsi', 'price': 50.00},
    ],
    "KFC": [
        {'name': 'Original Recipe Chicken', 'category': 'chicken', 'description': '2-piece fried chicken', 'price': 140.00},
        {'name': 'Zinger Burger', 'category': 'burger', 'description': 'Spicy chicken burger', 'price': 130.00},
        {'name': 'Popcorn Chicken', 'category': 'chicken', 'description': 'Bite-sized crispy chicken', 'price': 100.00},
        {'name': 'Coleslaw', 'category': 'other', 'description': 'Fresh cabbage salad', 'price': 50.00},
        {'name': 'Iced Tea', 'category': 'drinks', 'description': 'Refreshing iced tea', 'price': 45.00},
    ],
    "Starbucks": [
        {'name': 'Caramel Macchiato', 'category': 'coffee', 'description': 'Espresso with vanilla and caramel', 'price': 180.00},
        {'name': 'Cappuccino', 'category': 'coffee', 'description': 'Espresso with steamed milk foam', 'price': 150.00},
        {'name': 'Chocolate Chip Cookie', 'category': 'dessert', 'description': 'Freshly baked cookie', 'price': 90.00},
        {'name': 'Blueberry Muffin', 'category': 'dessert', 'description': 'Moist muffin with blueberries', 'price': 110.00},
        {'name': 'Iced Latte', 'category': 'coffee', 'description': 'Cold espresso with milk', 'price': 160.00},
    ],
    "Subway": [
        {'name': 'Italian BMT', 'category': 'sandwich', 'description': 'Salami, pepperoni, and ham sub', 'price': 180.00},
        {'name': 'Chicken Teriyaki', 'category': 'sandwich', 'description': 'Grilled chicken with teriyaki sauce', 'price': 170.00},
        {'name': 'Veggie Delite', 'category': 'sandwich', 'description': 'Fresh vegetables sub', 'price': 140.00},
        {'name': 'Cookies', 'category': 'dessert', 'description': 'Chocolate chip cookies', 'price': 60.00},
        {'name': 'Bottled Water', 'category': 'drinks', 'description': 'Mineral water', 'price': 30.00},
    ],
}

for store_name, items in menu_data.items():
    try:
        store = Store.objects.get(name=store_name)
        for item_data in items:
            if not MenuItem.objects.filter(store=store, name=item_data['name']).exists():
                MenuItem.objects.create(
                    store=store,
                    **item_data
                )
                print(f"✓ Added {item_data['name']} to {store_name}")
            else:
                print(f"- {item_data['name']} already exists in {store_name}")
    except Store.DoesNotExist:
        print(f"✗ Store {store_name} not found")

print("\n✅ Sample menu items added! You can now test ordering.")
print("Login to admin panel to add more items or upload images.")
