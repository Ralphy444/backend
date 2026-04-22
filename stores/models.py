from django.db import models
from accounts.models import User

# Fixed predefined categories - no dynamic adding
RESTAURANT_CATEGORIES = [
    ('Burgers', '🍔'),
    ('Chicken', '🍗'),
    ('Pizza', '🍕'),
    ('Fries', '🍟'),
    ('Drinks', '🥤'),
    ('Breakfast', '🍳'),
    ('Desserts', '🍰'),
    ('Coffee', '☕'),
    ('Pasta', '🍝'),
    ('Rice Meals', '🍚'),
    ('Seafood', '🦐'),
    ('Salads', '🥗'),
    ('Noodles', '🍜'),
    ('Sandwiches', '🥪'),
    ('Snacks', '🍿'),
    ('Others', '🍽️'),
]

class Restaurant(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='restaurant_images/', blank=True, null=True)
    category = models.CharField(max_length=50)
    delivery_time = models.CharField(max_length=20)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='managed_restaurants')
    is_active = models.BooleanField(default=True)
    is_24hrs = models.BooleanField(default=False)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image:
            self._resize_image()

    def _resize_image(self):
        try:
            from PIL import Image as PilImage, ImageOps
            import os
            img_path = self.image.path
            img = PilImage.open(img_path).convert('RGBA')
            # Pad to square with white background
            size = max(img.width, img.height)
            bg = PilImage.new('RGBA', (size, size), (255, 255, 255, 255))
            offset = ((size - img.width) // 2, (size - img.height) // 2)
            bg.paste(img, offset, mask=img)
            # Resize to fixed 400x400
            bg = bg.resize((400, 400), PilImage.LANCZOS).convert('RGB')
            bg.save(img_path, 'JPEG', quality=90)
        except Exception:
            pass
    @property
    def is_open(self):
        if not self.is_active:
            return False
        if self.is_24hrs:
            return True
        if not self.opening_time or not self.closing_time:
            return False  # no schedule set = closed by default
        from django.utils import timezone
        now = timezone.localtime(timezone.now()).time()
        if self.opening_time <= self.closing_time:
            return self.opening_time <= now <= self.closing_time
        return now >= self.opening_time or now <= self.closing_time

class MenuCategory(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_categories')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"

    class Meta:
        unique_together = ('restaurant', 'name')

class MenuItem(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    category = models.ForeignKey(MenuCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='menu_images/', blank=True, null=True)
    stock_quantity = models.IntegerField(default=100)
    available = models.BooleanField(default=True)
    addons = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image:
            self._resize_image()

    def _resize_image(self):
        try:
            from PIL import Image as PilImage
            img_path = self.image.path
            img = PilImage.open(img_path).convert('RGBA')
            size = max(img.width, img.height)
            bg = PilImage.new('RGBA', (size, size), (255, 255, 255, 255))
            bg.paste(img, ((size - img.width) // 2, (size - img.height) // 2), mask=img)
            bg.resize((400, 400), PilImage.LANCZOS).convert('RGB').save(img_path, 'JPEG', quality=90)
        except Exception:
            pass

    @property
    def in_stock(self):
        return int(self.stock_quantity) > 0


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted - Preparing'),
        ('ready', 'Ready for Delivery'),
        ('delivering', 'Out for Delivery'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('GCASH', 'GCash'),
        ('CARD', 'Credit/Debit Card'),
    ]

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='orders')
    delivery_rider = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries', limit_choices_to={'user_type': 'delivery'})
    items = models.JSONField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='COD')
    delivery_address = models.TextField()
    delivery_latitude = models.FloatField(null=True, blank=True)
    delivery_longitude = models.FloatField(null=True, blank=True)
    delivery_notes = models.TextField(blank=True)
    delivery_landmarks = models.JSONField(default=list, blank=True)
    delivery_location_source = models.JSONField(default=dict, blank=True)
    delivery_location_data = models.JSONField(default=dict, blank=True)
    delivery_zone_name = models.CharField(max_length=100, blank=True)
    is_within_delivery_zone = models.BooleanField(null=True, blank=True)
    reference_number = models.CharField(max_length=20, unique=True, blank=True)
    is_notified = models.BooleanField(default=False)
    rider_latitude = models.FloatField(null=True, blank=True)
    rider_longitude = models.FloatField(null=True, blank=True)
    delivery_proof = models.ImageField(upload_to='delivery_proofs/', null=True, blank=True)
    scheduled_time = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.reference_number:
            import random, string
            self.reference_number = 'ORD-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} - {self.reference_number} - {self.customer.username}"

    class Meta:
        ordering = ['-created_at']


class Rating(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='rating')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings_given')
    rider = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ratings_received')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.SET_NULL, null=True, blank=True, related_name='ratings')
    rider_stars = models.IntegerField(default=5)
    restaurant_stars = models.IntegerField(default=5)
    rider_comment = models.TextField(blank=True)
    restaurant_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.username} rated order #{self.order.id}"


class Message(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.message[:30]}"


class SukiConfig(models.Model):
    """Singleton — super admin editable Suki Points rules."""

    # --- EARNING ---
    points_per_peso = models.DecimalField(
        max_digits=8, decimal_places=4, default=0.05,
        help_text=(
            'Points earned per ₱1 spent. '
            'Examples: 0.05 = 1pt per ₱20 | 0.1 = 1pt per ₱10 | 0.5 = 1pt per ₱2 | 1.0 = 1pt per ₱1'
        )
    )

    # --- REDEEMING ---
    minimum_points_to_redeem = models.PositiveIntegerField(
        default=100,
        help_text='Minimum points a customer must have before they can redeem. Example: 100'
    )
    peso_value_per_point = models.DecimalField(
        max_digits=8, decimal_places=2, default=0.20,
        help_text=(
            'How much ₱ discount 1 point gives. '
            'Examples: 0.20 = 1pt = ₱0.20 | 1.0 = 1pt = ₱1 | 2.0 = 1pt = ₱2'
        )
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Suki Points Configuration'
        verbose_name_plural = 'Suki Points Configuration'

    def __str__(self):
        return (
            f'Earn: {self.points_per_peso} pts/₱1 | '
            f'Min redeem: {self.minimum_points_to_redeem} pts | '
            f'Value: 1pt = ₱{self.peso_value_per_point}'
        )

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SukiPoints(models.Model):
    """Loyalty points wallet — 1 point per ₱1 spent."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='suki_points')
    balance = models.IntegerField(default=0)
    total_earned = models.IntegerField(default=0)
    total_redeemed = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.balance} pts"


class SukiTransaction(models.Model):
    TYPE_CHOICES = [('earn', 'Earned'), ('redeem', 'Redeemed')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='suki_transactions')
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    points = models.IntegerField()          # positive = earned, negative = redeemed
    description = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} {self.type} {self.points} pts"


class AddressBook(models.Model):
    ICON_CHOICES = [
        ('home', '🏠 Home'),
        ('work', '💼 Work'),
        ('school', '🏫 School'),
        ('other', '📍 Other'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='address_book')
    label = models.CharField(max_length=50)          # e.g. "Home", "Work", custom
    icon = models.CharField(max_length=10, choices=ICON_CHOICES, default='other')
    address = models.TextField()
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', 'label']

    def __str__(self):
        return f"{self.user.username} - {self.label}"


class SavedLocation(models.Model):
    SOURCE_CHOICES = [
        ('user', 'User Submitted'),
        ('google', 'Google Maps'),
        ('osm', 'OpenStreetMap'),
        ('hybrid', 'Hybrid'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_locations', null=True, blank=True)
    label = models.CharField(max_length=120, blank=True)
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    notes = models.TextField(blank=True)
    landmarks = models.JSONField(default=list, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='user')
    source_details = models.JSONField(default=dict, blank=True)
    search_text = models.TextField(blank=True)
    usage_count = models.PositiveIntegerField(default=1)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        searchable_parts = [
            self.label,
            self.address,
            self.notes,
            ' '.join(self.landmarks or []),
        ]
        self.search_text = ' '.join(part.strip() for part in searchable_parts if part).strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.label or self.address[:60]

    class Meta:
        ordering = ['-last_used_at', '-updated_at']
