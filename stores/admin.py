from django.contrib import admin
from .models import Restaurant, MenuItem, Order, SavedLocation, MenuCategory, Message, SukiConfig


@admin.register(SukiConfig)
class SukiConfigAdmin(admin.ModelAdmin):
    list_display = ['points_per_peso', 'minimum_points_to_redeem', 'peso_value_per_point', 'earn_example', 'redeem_example', 'updated_at']
    fields = ['points_per_peso', 'minimum_points_to_redeem', 'peso_value_per_point']
    readonly_fields = []

    def has_add_permission(self, request):
        return not SukiConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect
        cfg = SukiConfig.get()
        return redirect(f'/admin/stores/sukiconfig/{cfg.pk}/change/')

    def earn_example(self, obj):
        from django.utils.safestring import mark_safe
        pts = float(obj.points_per_peso) * 100
        return mark_safe(f'<span style="color:green">₱100 order = <b>{pts:.2f} pts</b></span>')
    earn_example.short_description = '📦 Earn Example (₱100 order)'

    def redeem_example(self, obj):
        from django.utils.safestring import mark_safe
        discount = float(obj.minimum_points_to_redeem) * float(obj.peso_value_per_point)
        return mark_safe(
            f'<span style="color:#00B894">'
            f'Need <b>{obj.minimum_points_to_redeem} pts</b> min → '
            f'<b>{obj.minimum_points_to_redeem} pts = ₱{discount:.2f} off</b>'
            f'</span>'
        )
    redeem_example.short_description = '🎁 Redeem Example'

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'admin', 'delivery_time', 'is_active', 'is_24hrs', 'opening_time', 'closing_time', 'created_at']
    list_filter = ['category', 'is_active', 'is_24hrs']
    search_fields = ['name']
    fields = ['name', 'description', 'image', 'category', 'delivery_time', 'admin', 'is_active', 'is_24hrs', 'opening_time', 'closing_time', 'latitude', 'longitude']

@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'restaurant']
    list_filter = ['restaurant']
    search_fields = ['name']

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'restaurant', 'category', 'price', 'stock_quantity', 'available']
    list_filter = ['restaurant', 'category', 'available']
    search_fields = ['name']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['reference_number', 'customer', 'restaurant', 'total_price', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'payment_method']
    search_fields = ['reference_number', 'customer__username']


@admin.register(SavedLocation)
class SavedLocationAdmin(admin.ModelAdmin):
    list_display = ['label', 'user', 'source', 'usage_count', 'is_public', 'updated_at']
    list_filter = ['source', 'is_public']
    search_fields = ['label', 'address', 'notes', 'search_text']
