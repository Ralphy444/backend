from rest_framework import serializers
from .location_services import build_navigation_links
from .models import Restaurant, MenuItem, Order, SavedLocation, AddressBook, SukiPoints, SukiTransaction, SukiConfig, RESTAURANT_CATEGORIES, MenuCategory, Message, Rating

class MenuCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuCategory
        fields = ['id', 'name']

class MenuItemSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    in_stock = serializers.BooleanField(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    addons = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'category', 'category_name', 'description', 'price', 'image_url', 'stock_quantity', 'in_stock', 'available', 'addons', 'created_at']

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            url = obj.image.url
            if request and not str(url).startswith(('http://', 'https://')):
                return request.build_absolute_uri(url)
            return url
        return None

    def get_addons(self, obj):
        """Return addons as-is — supports both new grouped dict and legacy flat list."""
        import json
        raw = obj.addons
        if not raw:
            return None
        if isinstance(raw, (dict, list)):
            return raw
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                return None
        return None

class RestaurantSerializer(serializers.ModelSerializer):
    menu_items = MenuItemSerializer(many=True, read_only=True)
    image_url = serializers.SerializerMethodField()
    admin_name = serializers.CharField(source='admin.username', read_only=True)
    avg_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'description', 'image_url', 'category', 'delivery_time',
                  'admin', 'admin_name', 'is_active', 'is_24hrs', 'opening_time', 'closing_time',
                  'is_open', 'latitude', 'longitude', 'avg_rating', 'rating_count',
                  'menu_items', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            url = obj.image.url
            if request and not str(url).startswith(('http://', 'https://')):
                return request.build_absolute_uri(url)
            return url
        return None

    def get_avg_rating(self, obj):
        from django.db.models import Avg
        result = obj.ratings.aggregate(avg=Avg('restaurant_stars'))
        return round(result['avg'], 1) if result['avg'] else None

    def get_rating_count(self, obj):
        return obj.ratings.count()

class OrderSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    customer_name = serializers.CharField(source='customer.username', read_only=True)
    delivery_rider_info = serializers.SerializerMethodField()
    delivery_coordinates = serializers.SerializerMethodField()
    restaurant_coordinates = serializers.SerializerMethodField()
    navigation_links = serializers.SerializerMethodField()
    delivery_proof_url = serializers.SerializerMethodField()
    eta_minutes = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    restaurant_id = serializers.IntegerField(source='restaurant.id', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'customer', 'customer_name', 'restaurant', 'restaurant_id', 'restaurant_name',
                  'items', 'total_price', 'status', 'delivery_address', 'payment_method', 'reference_number',
                  'delivery_notes', 'delivery_landmarks', 'delivery_location_source', 'delivery_location_data',
                  'delivery_zone_name', 'is_within_delivery_zone', 'delivery_coordinates',
                  'restaurant_coordinates', 'navigation_links', 'delivery_rider_info',
                  'rider_latitude', 'rider_longitude', 'delivery_proof_url', 'cancel_reason',
                  'scheduled_time', 'eta_minutes', 'rating', 'created_at', 'updated_at']
        read_only_fields = ['customer', 'restaurant', 'created_at', 'updated_at']

    def get_rating(self, obj):
        try:
            r = obj.rating
            return {
                'rider_stars': r.rider_stars,
                'restaurant_stars': r.restaurant_stars,
                'rider_comment': r.rider_comment,
                'restaurant_comment': r.restaurant_comment,
            }
        except Exception:
            return None

    def get_delivery_proof_url(self, obj):
        if obj.delivery_proof:
            request = self.context.get('request')
            url = obj.delivery_proof.url
            if request and not str(url).startswith(('http://', 'https://')):
                return request.build_absolute_uri(url)
            return url
        return None

    def get_delivery_rider_info(self, obj):
        if obj.delivery_rider and obj.status in ['delivering', 'completed']:
            from django.db.models import Avg, Count
            stats = Rating.objects.filter(rider=obj.delivery_rider).aggregate(avg=Avg('rider_stars'), count=Count('id'))
            return {
                'first_name': obj.delivery_rider.first_name,
                'last_name': obj.delivery_rider.last_name,
                'motorcycle_color': obj.delivery_rider.motorcycle_color,
                'plate_number': obj.delivery_rider.plate_number,
                'driver_license': obj.delivery_rider.driver_license,
                'rating_avg': round(stats['avg'] or 0, 1),
                'rating_count': stats['count'],
            }
        return None

    def get_delivery_coordinates(self, obj):
        if obj.delivery_latitude is None or obj.delivery_longitude is None:
            return None
        return {'lat': obj.delivery_latitude, 'lng': obj.delivery_longitude}

    def get_restaurant_coordinates(self, obj):
        if obj.restaurant.latitude and obj.restaurant.longitude:
            return {'lat': float(obj.restaurant.latitude), 'lng': float(obj.restaurant.longitude)}
        admin = getattr(obj.restaurant, 'admin', None)
        if not admin or admin.latitude is None or admin.longitude is None:
            return None
        return {'lat': float(admin.latitude), 'lng': float(admin.longitude)}

    def get_navigation_links(self, obj):
        return build_navigation_links(obj.delivery_latitude, obj.delivery_longitude)

    def get_eta_minutes(self, obj):
        if obj.status != 'delivering':
            return None
        if not obj.rider_latitude or not obj.rider_longitude:
            return None
        if not obj.delivery_latitude or not obj.delivery_longitude:
            return None
        from .location_services import haversine_distance_m
        distance_m = haversine_distance_m(
            float(obj.rider_latitude), float(obj.rider_longitude),
            float(obj.delivery_latitude), float(obj.delivery_longitude)
        )
        minutes = round(distance_m / 500)
        return max(1, minutes)

class DeliveryOrderSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    customer_info = serializers.SerializerMethodField()
    delivery_coordinates = serializers.SerializerMethodField()
    restaurant_coordinates = serializers.SerializerMethodField()
    navigation_links = serializers.SerializerMethodField()
    rider_rating = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'reference_number', 'restaurant', 'restaurant_name',
                  'items', 'total_price', 'status', 'delivery_address', 'payment_method',
                  'delivery_notes', 'delivery_landmarks', 'delivery_zone_name', 'is_within_delivery_zone',
                  'delivery_coordinates', 'restaurant_coordinates', 'navigation_links',
                  'customer_info', 'rider_rating', 'created_at', 'updated_at']

    def get_rider_rating(self, obj):
        if obj.status != 'completed':
            return None
        try:
            r = obj.rating
            return {'stars': r.rider_stars, 'comment': r.rider_comment}
        except Exception:
            return None

    def get_customer_info(self, obj):
        return {
            'name': f"{obj.customer.first_name} {obj.customer.last_name}".strip() or obj.customer.username,
            'phone': obj.customer.phone,
            'address': obj.delivery_address,
        }

    def get_delivery_coordinates(self, obj):
        if obj.delivery_latitude is None or obj.delivery_longitude is None:
            return None
        return {'lat': obj.delivery_latitude, 'lng': obj.delivery_longitude}

    def get_restaurant_coordinates(self, obj):
        if obj.restaurant.latitude and obj.restaurant.longitude:
            return {'lat': float(obj.restaurant.latitude), 'lng': float(obj.restaurant.longitude)}
        admin = getattr(obj.restaurant, 'admin', None)
        if not admin or admin.latitude is None or admin.longitude is None:
            return None
        return {'lat': float(admin.latitude), 'lng': float(admin.longitude)}

    def get_navigation_links(self, obj):
        return build_navigation_links(obj.delivery_latitude, obj.delivery_longitude)


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['id', 'rider_stars', 'restaurant_stars', 'rider_comment', 'restaurant_comment', 'created_at']

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    sender_type = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'sender_name', 'sender_type', 'message', 'created_at']

    def get_sender_type(self, obj):
        return obj.sender.user_type

class SavedLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedLocation
        fields = [
            'id', 'label', 'address', 'latitude', 'longitude', 'notes', 'landmarks',
            'source', 'source_details', 'usage_count', 'created_at', 'updated_at',
        ]


class AddressBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddressBook
        fields = ['id', 'label', 'icon', 'address', 'latitude', 'longitude', 'notes', 'is_default', 'created_at']
        read_only_fields = ['id', 'created_at']
