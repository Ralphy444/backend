import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from accounts.models import User

# Update delivery riders with sample information
delivery_riders = User.objects.filter(user_type='delivery')

if delivery_riders.exists():
    for idx, rider in enumerate(delivery_riders, 1):
        rider.motorcycle_color = f"Red Honda" if idx % 2 == 0 else "Blue Yamaha"
        rider.plate_number = f"ABC-{1000 + idx}"
        rider.driver_license = f"N01-{90 + idx}-{100000 + idx}"
        rider.save()
        print(f"Updated {rider.username}: {rider.motorcycle_color}, {rider.plate_number}, {rider.driver_license}")
    print(f"\nSuccessfully updated {delivery_riders.count()} delivery riders!")
else:
    print("No delivery riders found. Create delivery riders first.")
