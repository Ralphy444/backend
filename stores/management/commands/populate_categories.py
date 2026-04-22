from django.core.management.base import BaseCommand
from stores.models import Category


class Command(BaseCommand):
    help = 'Populate default food categories'

    def handle(self, *args, **kwargs):
        categories = [
            {'name': 'Burger', 'icon': '🍔', 'description': 'Delicious burgers'},
            {'name': 'Chicken', 'icon': '🍗', 'description': 'Fried and grilled chicken'},
            {'name': 'Pizza', 'icon': '🍕', 'description': 'Hot and fresh pizzas'},
            {'name': 'Drinks', 'icon': '🥤', 'description': 'Refreshing beverages'},
            {'name': 'Fries', 'icon': '🍟', 'description': 'Crispy french fries'},
            {'name': 'Sandwich', 'icon': '🥪', 'description': 'Fresh sandwiches'},
            {'name': 'Dessert', 'icon': '🍰', 'description': 'Sweet treats'},
            {'name': 'Coffee', 'icon': '☕', 'description': 'Hot and cold coffee'},
            {'name': 'Pasta', 'icon': '🍝', 'description': 'Italian pasta dishes'},
            {'name': 'Rice Meals', 'icon': '🍚', 'description': 'Complete rice meals'},
            {'name': 'Seafood', 'icon': '🦐', 'description': 'Fresh seafood dishes'},
            {'name': 'Salad', 'icon': '🥗', 'description': 'Healthy salads'},
            {'name': 'Noodles', 'icon': '🍜', 'description': 'Asian noodle dishes'},
            {'name': 'Breakfast', 'icon': '🍳', 'description': 'Breakfast items'},
            {'name': 'Other', 'icon': '🍽️', 'description': 'Other food items'},
        ]
        
        created_count = 0
        for cat_data in categories:
            category, created = Category.objects.get_or_create(
                name=cat_data['name'],
                defaults={'icon': cat_data['icon'], 'description': cat_data['description']}
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))
        
        self.stdout.write(self.style.SUCCESS(f'\nTotal categories created: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'Total categories in database: {Category.objects.count()}'))
