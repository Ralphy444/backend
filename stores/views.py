from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.conf import settings as django_settings
from .location_services import merge_location_results, search_google_locations, search_osm_locations, search_saved_locations, zone_status
from .models import Restaurant, MenuItem, Order, SavedLocation, AddressBook, SukiPoints, SukiTransaction, SukiConfig, RESTAURANT_CATEGORIES, MenuCategory, Message, Rating
from .serializers import RestaurantSerializer, MenuItemSerializer, OrderSerializer, DeliveryOrderSerializer, SavedLocationSerializer, AddressBookSerializer, MenuCategorySerializer, MessageSerializer, RatingSerializer
from accounts.models import User
import urllib.request
import urllib.error
import json
import base64

def send_push_notification(push_token, title, body):
    if not push_token or not push_token.startswith('ExponentPushToken'):
        return
    try:
        payload = json.dumps({
            'to': push_token,
            'title': title,
            'body': body,
            'sound': 'default',
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://exp.host/--/api/v2/push/send',
            data=payload,
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
            method='POST'
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def manage_restaurants(request):
    """Super admin: list all restaurants or create a new one."""
    if not request.user.is_staff:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    if request.method == 'GET':
        restaurants = Restaurant.objects.all().order_by('-created_at')
        serializer = RestaurantSerializer(restaurants, many=True, context={'request': request})
        return Response(serializer.data)
    # POST - create restaurant
    try:
        admin_user = User.objects.get(id=request.data.get('admin_id'), user_type='store_admin')
    except User.DoesNotExist:
        return Response({'error': 'Store admin user not found'}, status=status.HTTP_404_NOT_FOUND)
    category_name = request.data.get('category', '')
    restaurant = Restaurant.objects.create(
        name=request.data.get('name'),
        description=request.data.get('description', ''),
        category=category_name,
        delivery_time=request.data.get('delivery_time', '30-45 mins'),
        admin=admin_user,
    )
    if 'image' in request.FILES:
        restaurant.image = request.FILES['image']
        restaurant.save(update_fields=['image'])
    return Response(RestaurantSerializer(restaurant, context={'request': request}).data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_store_admins(request):
    """Super admin: list all users with user_type=store_admin."""
    if not request.user.is_staff:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    users = User.objects.filter(user_type='store_admin').values('id', 'username', 'first_name', 'last_name', 'email')
    return Response(list(users))

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def manage_restaurant_settings(request, restaurant_id):
    try:
        if request.user.is_staff:
            restaurant = Restaurant.objects.get(id=restaurant_id)
        else:
            restaurant = Restaurant.objects.get(id=restaurant_id, admin=request.user)
        for field in ['opening_time', 'closing_time', 'is_24hrs']:
            if field in request.data:
                val = request.data[field]
                if field in ['opening_time', 'closing_time']:
                    setattr(restaurant, field, val if val else None)
                else:
                    setattr(restaurant, field, val)
        if 'is_active' in request.data:
            restaurant.is_active = request.data['is_active']
        restaurant.save()
        return Response({'message': 'Store settings updated', 'is_active': restaurant.is_active, 'is_open': restaurant.is_open})
    except Restaurant.DoesNotExist:
        return Response({'error': 'Restaurant not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([AllowAny])
def store_list(request):
    restaurants = Restaurant.objects.filter(is_active=True)
    serializer = RestaurantSerializer(restaurants, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def store_detail(request, store_id):
    try:
        restaurant = Restaurant.objects.get(id=store_id)
        serializer = RestaurantSerializer(restaurant, context={'request': request})
        return Response(serializer.data)
    except Restaurant.DoesNotExist:
        return Response({'error': 'Restaurant not found'}, status=404)

@api_view(['GET'])
@permission_classes([AllowAny])
def store_menu(request, store_id):
    menu_items = MenuItem.objects.filter(restaurant_id=store_id, available=True)
    serializer = MenuItemSerializer(menu_items, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_categories(request):
    categories = [{'name': name, 'icon': icon} for name, icon in RESTAURANT_CATEGORIES]
    return Response(categories)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order(request):
    try:
        restaurant_id = request.data.get('restaurant') or request.data.get('store')
        restaurant = Restaurant.objects.get(id=restaurant_id)
        delivery_latitude = request.data.get('delivery_lat')
        delivery_longitude = request.data.get('delivery_lng')
        try:
            delivery_latitude = float(delivery_latitude) if delivery_latitude is not None else None
            delivery_longitude = float(delivery_longitude) if delivery_longitude is not None else None
        except (TypeError, ValueError):
            return Response({'error': 'Invalid delivery coordinates'}, status=status.HTTP_400_BAD_REQUEST)

        landmarks = request.data.get('delivery_landmarks', [])
        if isinstance(landmarks, str):
            landmarks = [landmarks] if landmarks else []
        location_source = request.data.get('delivery_location_source', {})
        location_data = request.data.get('delivery_location_data', {})
        zone = zone_status(delivery_latitude, delivery_longitude)
        # Handle Suki Points redemption
        try:
            redeem_points = int(float(request.data.get('redeem_points', 0) or 0))
        except (TypeError, ValueError):
            redeem_points = 0
        points_discount = 0.0
        if redeem_points > 0:
            wallet, _ = SukiPoints.objects.get_or_create(user=request.user)
            cfg = SukiConfig.get()
            # Enforce minimum points threshold
            if wallet.balance < cfg.minimum_points_to_redeem:
                redeem_points = 0
            else:
                redeem_points = min(redeem_points, wallet.balance)
                points_discount = float(redeem_points) * float(cfg.peso_value_per_point)
        total_price = float(request.data.get('total_price', '0')) - points_discount
        total_price = max(0, total_price)
        order = Order.objects.create(
            customer=request.user,
            restaurant=restaurant,
            items=request.data.get('items', []),
            total_price=str(round(total_price, 2)),
            delivery_address=request.data.get('delivery_address', ''),
            delivery_latitude=delivery_latitude,
            delivery_longitude=delivery_longitude,
            delivery_notes=request.data.get('delivery_notes', ''),
            delivery_landmarks=landmarks,
            delivery_location_source=location_source if isinstance(location_source, dict) else {},
            delivery_location_data=location_data if isinstance(location_data, dict) else {},
            delivery_zone_name=zone['zone_name'],
            is_within_delivery_zone=zone['in_zone'],
            payment_method=request.data.get('payment_method', 'COD'),
            scheduled_time=request.data.get('scheduled_time') or None,
        )
        # Deduct redeemed points
        if redeem_points > 0:
            wallet.balance -= redeem_points
            wallet.total_redeemed += redeem_points
            wallet.save()
            SukiTransaction.objects.create(
                user=request.user, order=order, type='redeem',
                points=-redeem_points,
                description=f'Redeemed for Order #{order.reference_number}'
            )
        if delivery_latitude is not None and delivery_longitude is not None:
            SavedLocation.objects.create(
                user=request.user,
                label=request.data.get('delivery_label', '') or request.data.get('delivery_address', ''),
                address=request.data.get('delivery_address', ''),
                latitude=delivery_latitude,
                longitude=delivery_longitude,
                notes=request.data.get('delivery_notes', ''),
                landmarks=landmarks,
                source='hybrid' if location_source else 'user',
                source_details=location_source if isinstance(location_source, dict) else {},
            )
        # Notify store admin
        send_push_notification(
            restaurant.admin.push_token,
            '🛎️ New Order!',
            f'New order #{order.reference_number} received!'
        )
        return Response({
            'id': order.id,
            'reference_number': order.reference_number,
            'status': order.status,
            'total_price': str(order.total_price),
            'restaurant_name': restaurant.name,
            'is_within_delivery_zone': order.is_within_delivery_zone,
        }, status=status.HTTP_201_CREATED)
    except Restaurant.DoesNotExist:
        return Response({'error': 'Restaurant not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_orders(request):
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_detail(request, order_id):
    try:
        order = Order.objects.get(id=order_id, customer=request.user)
        return Response(OrderSerializer(order).data)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def store_orders(request, store_id):
    try:
        if request.user.is_staff:
            restaurant = Restaurant.objects.get(id=store_id)
        else:
            restaurant = Restaurant.objects.get(id=store_id, admin=request.user)
        from django.utils import timezone
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(hours=24)
        orders = Order.objects.filter(restaurant=restaurant).exclude(
            status='completed', updated_at__lt=cutoff
        ).order_by('-created_at')
        new_orders_count = orders.filter(is_notified=False, status='pending').count()
        orders.filter(is_notified=False).update(is_notified=True)
        serializer = OrderSerializer(orders, many=True)
        return Response({'orders': serializer.data, 'new_orders_count': new_orders_count})
    except Restaurant.DoesNotExist:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_order_status(request, order_id):
    try:
        if request.user.is_staff:
            order = Order.objects.get(id=order_id)
        else:
            order = Order.objects.get(id=order_id, restaurant__admin=request.user)
        new_status = request.data.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            # Notify customer
            notifs = {
                'accepted': ('👨🍳 Order Confirmed!', 'Restaurant is preparing your food.'),
                'ready': ('✅ Order Ready!', 'Waiting for a rider to pick up your order.'),
                'delivering': ('🛵 Rider On the Way!', 'Your food is coming!'),
                'completed': ('🎉 Order Delivered!', 'Enjoy your meal! Please rate your rider.'),
                'cancelled': ('❌ Order Cancelled', 'Your order has been cancelled.'),
            }
            if new_status in notifs:
                title, body = notifs[new_status]
                send_push_notification(order.customer.push_token, title, body)
            # Notify all delivery riders when order is ready
            if new_status == 'ready':
                for rider in User.objects.filter(user_type='delivery', is_active=True).exclude(push_token=''):
                    send_push_notification(rider.push_token, '📦 New Delivery Available!', f'Order from {order.restaurant.name} is ready for pickup!')
            return Response(OrderSerializer(order).data)
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id, customer=request.user)
        if order.status != 'pending':
            return Response({'error': 'Order can no longer be cancelled once accepted by the restaurant.'}, status=status.HTTP_400_BAD_REQUEST)
        reason = request.data.get('reason', '').strip()
        if not reason:
            return Response({'error': 'Please provide a reason for cancellation.'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'cancelled'
        order.cancel_reason = reason
        order.save()
        # Notify store admin
        send_push_notification(
            order.restaurant.admin.push_token,
            '❌ Order Cancelled',
            f'Order #{order.reference_number} was cancelled. Reason: {reason}'
        )
        return Response({'message': 'Order cancelled successfully'})
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def delivery_orders(request):
    available_orders = Order.objects.filter(status='ready').order_by('-created_at')
    my_deliveries = Order.objects.filter(delivery_rider=request.user, status__in=['delivering', 'completed']).order_by('-created_at')
    return Response({
        'available_orders': DeliveryOrderSerializer(available_orders, many=True).data,
        'my_deliveries': DeliveryOrderSerializer(my_deliveries, many=True).data,
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_delivery(request, order_id):
    if request.user.user_type != 'delivery':
        return Response({'error': 'Only delivery riders can accept orders'}, status=status.HTTP_403_FORBIDDEN)
    try:
        order = Order.objects.get(id=order_id, status='ready')
        order.delivery_rider = request.user
        order.status = 'delivering'
        order.save()
        return Response(DeliveryOrderSerializer(order).data)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found or already taken by another rider'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_rider_location(request, order_id):
    try:
        order = Order.objects.get(id=order_id, delivery_rider=request.user, status='delivering')
        order.rider_latitude = request.data.get('latitude')
        order.rider_longitude = request.data.get('longitude')
        order.save(update_fields=['rider_latitude', 'rider_longitude'])
        return Response({'status': 'ok'})
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_delivery(request, order_id):
    try:
        order = Order.objects.get(id=order_id, delivery_rider=request.user, status='delivering')
        if 'proof_image' in request.FILES:
            order.delivery_proof = request.FILES['proof_image']
        order.status = 'completed'
        order.save()
        # Deduct stock for each ordered item
        for item in order.items:
            try:
                menu_item = MenuItem.objects.get(id=item['id'], restaurant=order.restaurant)
                qty = int(item.get('quantity', 1))
                menu_item.stock_quantity = max(0, int(menu_item.stock_quantity) - qty)
                menu_item.save(update_fields=['stock_quantity'])
            except MenuItem.DoesNotExist:
                pass
        # Award Suki Points using admin-configurable rate
        cfg = SukiConfig.get()
        points_earned = max(1, int(float(order.total_price) * float(cfg.points_per_peso)))
        wallet, _ = SukiPoints.objects.get_or_create(user=order.customer)
        wallet.balance += points_earned
        wallet.total_earned += points_earned
        wallet.save()
        SukiTransaction.objects.create(
            user=order.customer, order=order, type='earn',
            points=points_earned,
            description=f'Order #{order.reference_number} completed'
        )
        send_push_notification(
            order.customer.push_token,
            '🌟 Suki Points Earned!',
            f'You earned {points_earned} Suki Points from your order!'
        )
        return Response(DeliveryOrderSerializer(order).data)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_rating(request, order_id):
    try:
        order = Order.objects.get(id=order_id, customer=request.user, status='completed')
    except Order.DoesNotExist:
        return Response({'error': 'Order not found or not completed'}, status=status.HTTP_404_NOT_FOUND)
    if hasattr(order, 'rating'):
        return Response({'error': 'Already rated'}, status=status.HTTP_400_BAD_REQUEST)
    rider_stars = int(request.data.get('rider_stars', 5))
    restaurant_stars = int(request.data.get('restaurant_stars', 5))
    if not (1 <= rider_stars <= 5) or not (1 <= restaurant_stars <= 5):
        return Response({'error': 'Stars must be 1-5'}, status=status.HTTP_400_BAD_REQUEST)
    rating = Rating.objects.create(
        order=order,
        customer=request.user,
        rider=order.delivery_rider,
        restaurant=order.restaurant,
        rider_stars=rider_stars,
        restaurant_stars=restaurant_stars,
        rider_comment=request.data.get('rider_comment', ''),
        restaurant_comment=request.data.get('restaurant_comment', ''),
    )
    return Response(RatingSerializer(rating).data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([AllowAny])
def rider_rating(request, rider_id):
    from django.db.models import Avg, Count
    stats = Rating.objects.filter(rider_id=rider_id).aggregate(avg=Avg('rider_stars'), count=Count('id'))
    return Response({'average': round(stats['avg'] or 0, 1), 'count': stats['count']})

@api_view(['GET'])
@permission_classes([AllowAny])
def restaurant_rating(request, restaurant_id):
    from django.db.models import Avg, Count
    stats = Rating.objects.filter(restaurant_id=restaurant_id).aggregate(avg=Avg('restaurant_stars'), count=Count('id'))
    return Response({'average': round(stats['avg'] or 0, 1), 'count': stats['count']})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_gcash_payment(request):
    """Create a PayMongo GCash payment link and return the checkout URL."""
    amount = request.data.get('amount')  # in PHP pesos
    order_description = request.data.get('description', 'Food Order')
    try:
        amount_cents = int(float(amount) * 100)  # PayMongo uses centavos
    except (TypeError, ValueError):
        return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

    secret_key = django_settings.PAYMONGO_SECRET_KEY
    credentials = base64.b64encode(f'{secret_key}:'.encode()).decode()

    payload = json.dumps({
        'data': {
            'attributes': {
                'amount': amount_cents,
                'payment_method_types': ['gcash'],
                'description': order_description,
                'currency': 'PHP',
                'redirect': {
                    'success': 'foodordering://payment-success',
                    'failed': 'foodordering://payment-failed',
                }
            }
        }
    }).encode('utf-8')

    try:
        req = urllib.request.Request(
            'https://api.paymongo.com/v1/links',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Basic {credentials}',
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
        checkout_url = result['data']['attributes']['checkout_url']
        link_id = result['data']['id']
        return Response({'checkout_url': checkout_url, 'link_id': link_id})
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        return Response({'error': f'PayMongo error: {error_body}'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_gcash_payment(request, link_id):
    """Check if a PayMongo payment link has been paid."""
    secret_key = django_settings.PAYMONGO_SECRET_KEY
    credentials = base64.b64encode(f'{secret_key}:'.encode()).decode()
    try:
        req = urllib.request.Request(
            f'https://api.paymongo.com/v1/links/{link_id}',
            headers={'Authorization': f'Basic {credentials}'},
            method='GET'
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
        payment_status = result['data']['attributes']['status']
        return Response({'status': payment_status, 'paid': payment_status == 'paid'})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def order_messages(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        # Only customer or assigned rider can access
        if request.user != order.customer and request.user != order.delivery_rider:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
        if request.method == 'GET':
            messages = Message.objects.filter(order=order)
            return Response(MessageSerializer(messages, many=True).data)
        text = request.data.get('message', '').strip()
        if not text:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)
        msg = Message.objects.create(order=order, sender=request.user, message=text)
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([AllowAny])
def location_search(request):
    query = (request.GET.get('q') or '').strip()
    try:
        lat = float(request.GET.get('lat')) if request.GET.get('lat') else None
        lng = float(request.GET.get('lng')) if request.GET.get('lng') else None
    except ValueError:
        lat = None
        lng = None

    if len(query) < 2:
        return Response([])

    user_locations = search_saved_locations(query, lat=lat, lng=lng, limit=4)
    google_locations = search_google_locations(query, limit=4)
    osm_locations = search_osm_locations(query, limit=6)
    results = merge_location_results(user_locations, google_locations, osm_locations, limit=10)
    return Response(results)


@api_view(['GET'])
@permission_classes([AllowAny])
def check_delivery_zone(request):
    try:
        lat = float(request.GET.get('lat'))
        lng = float(request.GET.get('lng'))
    except (TypeError, ValueError):
        return Response({'error': 'lat and lng are required'}, status=status.HTTP_400_BAD_REQUEST)

    return Response(zone_status(lat, lng))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def saved_locations(request):
    queryset = SavedLocation.objects.filter(user=request.user).order_by('-last_used_at')[:20]
    return Response(SavedLocationSerializer(queryset, many=True).data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def address_book(request):
    if request.method == 'GET':
        entries = AddressBook.objects.filter(user=request.user)
        return Response(AddressBookSerializer(entries, many=True).data)
    # POST — create
    serializer = AddressBookSerializer(data=request.data)
    if serializer.is_valid():
        # If new entry is default, unset others
        if request.data.get('is_default'):
            AddressBook.objects.filter(user=request.user, is_default=True).update(is_default=False)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def address_book_detail(request, pk):
    try:
        entry = AddressBook.objects.get(pk=pk, user=request.user)
    except AddressBook.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'DELETE':
        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = AddressBookSerializer(entry, data=request.data, partial=True)
    if serializer.is_valid():
        if request.data.get('is_default'):
            AddressBook.objects.filter(user=request.user, is_default=True).update(is_default=False)
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def suki_balance(request):
    wallet, _ = SukiPoints.objects.get_or_create(user=request.user)
    transactions = SukiTransaction.objects.filter(user=request.user)[:20]
    cfg = SukiConfig.get()
    return Response({
        'balance': wallet.balance,
        'total_earned': wallet.total_earned,
        'total_redeemed': wallet.total_redeemed,
        'points_per_peso': float(cfg.points_per_peso),
        'minimum_points_to_redeem': cfg.minimum_points_to_redeem,
        'peso_value_per_point': float(cfg.peso_value_per_point),
        'can_redeem': wallet.balance >= cfg.minimum_points_to_redeem,
        'transactions': [
            {'type': t.type, 'points': t.points, 'description': t.description, 'created_at': t.created_at}
            for t in transactions
        ],
    })


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def manage_menu_categories(request):
    if request.method == 'GET' and request.GET.get('restaurant_id'):
        categories = MenuCategory.objects.filter(restaurant_id=request.GET.get('restaurant_id'))
        return Response(MenuCategorySerializer(categories, many=True).data)
    if not request.user.is_authenticated:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        if request.user.is_staff:
            restaurant = Restaurant.objects.get(id=request.GET.get('restaurant_id') or request.data.get('restaurant_id'))
        else:
            restaurant = Restaurant.objects.get(admin=request.user)
    except Restaurant.DoesNotExist:
        return Response({'error': 'Restaurant not found'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        categories = MenuCategory.objects.filter(restaurant=restaurant)
        return Response(MenuCategorySerializer(categories, many=True).data)
    name = request.data.get('name', '').strip()
    if not name:
        return Response({'error': 'Name is required'}, status=status.HTTP_400_BAD_REQUEST)
    category, created = MenuCategory.objects.get_or_create(restaurant=restaurant, name=name)
    return Response(MenuCategorySerializer(category).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_menu_category(request, category_id):
    try:
        category = MenuCategory.objects.get(id=category_id, restaurant__admin=request.user)
        category.delete()
        return Response({'message': 'Deleted'}, status=status.HTTP_204_NO_CONTENT)
    except MenuCategory.DoesNotExist:
        return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_menu_item(request):
    try:
        if request.user.is_staff:
            restaurant = Restaurant.objects.get(id=request.data.get('restaurant_id'))
        else:
            restaurant = Restaurant.objects.get(admin=request.user)
        category = None
        category_id = request.data.get('category')
        if category_id:
            try:
                category = MenuCategory.objects.get(id=category_id, restaurant=restaurant)
            except MenuCategory.DoesNotExist:
                pass
        addons_raw = request.data.get('addons', '[]')
        try:
            import json
            addons = json.loads(addons_raw) if isinstance(addons_raw, str) else addons_raw
        except Exception:
            addons = []
        menu_item = MenuItem.objects.create(
            restaurant=restaurant,
            name=request.data.get('name'),
            category=category,
            description=request.data.get('description', ''),
            price=request.data.get('price'),
            stock_quantity=request.data.get('stock_quantity', 100),
            addons=addons,
        )
        if 'image' in request.FILES:
            menu_item.image = request.FILES['image']
            menu_item.save()
        return Response(MenuItemSerializer(menu_item, context={'request': request}).data, status=status.HTTP_201_CREATED)
    except Restaurant.DoesNotExist:
        return Response({'error': 'Restaurant not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def manage_menu_item(request, item_id):
    try:
        if request.user.is_staff:
            menu_item = MenuItem.objects.get(id=item_id)
        else:
            menu_item = MenuItem.objects.get(id=item_id, restaurant__admin=request.user)
    except MenuItem.DoesNotExist:
        return Response({'error': 'Menu item not found'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        return Response(MenuItemSerializer(menu_item, context={'request': request}).data)
    elif request.method == 'PUT':
        for field in ['name', 'description', 'price', 'available']:
            if field in request.data:
                setattr(menu_item, field, request.data[field])
        if 'addons' in request.data:
            import json
            addons_raw = request.data['addons']
            try:
                menu_item.addons = json.loads(addons_raw) if isinstance(addons_raw, str) else addons_raw
            except Exception:
                menu_item.addons = addons_raw
        if 'stock_quantity' in request.data:
            try:
                menu_item.stock_quantity = int(request.data['stock_quantity'])
            except (ValueError, TypeError):
                pass
        if 'category' in request.data:
            try:
                menu_item.category = MenuCategory.objects.get(id=request.data['category'], restaurant=menu_item.restaurant)
            except MenuCategory.DoesNotExist:
                menu_item.category = None
        if 'image' in request.FILES:
            menu_item.image = request.FILES['image']
        menu_item.save()
        return Response(MenuItemSerializer(menu_item, context={'request': request}).data)
    elif request.method == 'DELETE':
        menu_item.delete()
        return Response({'message': 'Deleted'}, status=status.HTTP_204_NO_CONTENT)
