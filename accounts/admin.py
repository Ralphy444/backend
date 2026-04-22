from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.safestring import mark_safe
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'full_name', 'phone', 'user_type', 'is_active', 'date_joined', 'approval_status', 'duplicate_warning']
    list_filter = ['user_type', 'is_active', 'is_staff']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'plate_number', 'phone']
    ordering = ['-date_joined']
    actions = ['approve_riders', 'reject_riders']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Extra Info', {'fields': ('user_type', 'address', 'latitude', 'longitude')}),
        ('Rider Info', {'fields': ('motorcycle_color', 'plate_number', 'driver_license', 'motorcycle_photo_preview', 'license_photo_preview', 'face_left_preview', 'face_front_preview', 'face_right_preview', 'duplicate_check')}),
        ('Security', {'fields': ('failed_login_attempts', 'account_locked_until')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('username', 'password1', 'password2')}),
        ('Extra Info', {'fields': ('user_type', 'email', 'first_name', 'last_name', 'phone')}),
    )
    readonly_fields = ['motorcycle_photo_preview', 'license_photo_preview', 'face_left_preview', 'face_front_preview', 'face_right_preview', 'duplicate_check']

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or '-'
    full_name.short_description = 'Full Name'

    def approval_status(self, obj):
        if obj.user_type != 'delivery':
            return '-'
        if obj.is_active:
            return mark_safe('<span style="color:green;font-weight:bold;">✓ Approved</span>')
        return mark_safe('<span style="color:orange;font-weight:bold;">⏳ Pending</span>')
    approval_status.short_description = 'Approval'

    def _get_duplicates(self, obj):
        if obj.user_type != 'delivery':
            return []
        duplicates = []
        if obj.phone:
            for u in User.objects.filter(user_type='delivery', phone=obj.phone).exclude(id=obj.id):
                duplicates.append(f"Same phone: {u.username} ({u.first_name} {u.last_name})")
        if obj.first_name and obj.last_name:
            for u in User.objects.filter(user_type='delivery', first_name__iexact=obj.first_name, last_name__iexact=obj.last_name).exclude(id=obj.id):
                duplicates.append(f"Same name: {u.username} (Phone: {u.phone or 'N/A'})")
        if obj.plate_number:
            for u in User.objects.filter(user_type='delivery', plate_number__iexact=obj.plate_number).exclude(id=obj.id):
                duplicates.append(f"Same plate: {u.username} ({u.first_name} {u.last_name})")
        return duplicates

    def duplicate_warning(self, obj):
        if obj.user_type != 'delivery':
            return '-'
        if self._get_duplicates(obj):
            return mark_safe('<span style="color:red;font-weight:bold;">⚠️ Possible Duplicate</span>')
        return '-'
    duplicate_warning.short_description = '⚠️ Duplicate'

    def duplicate_check(self, obj):
        duplicates = self._get_duplicates(obj)
        if not duplicates:
            return mark_safe('<span style="color:green;font-weight:bold;">✓ No duplicates found</span>')
        items_html = ''.join(f'<li style="color:red;">{d}</li>' for d in duplicates)
        return mark_safe(
            f'<div style="background:#FFF3CD;padding:10px;border-radius:6px;border:1px solid #FFC107;">'
            f'<strong>⚠️ Possible duplicate accounts detected:</strong><ul>{items_html}</ul></div>'
        )
    duplicate_check.short_description = '⚠️ Duplicate Check'

    def motorcycle_photo_preview(self, obj):
        if obj.motorcycle_photo:
            return mark_safe(f'<img src="{obj.motorcycle_photo.url}" style="max-width:300px;max-height:200px;border-radius:8px;" />')
        return 'No photo uploaded'
    motorcycle_photo_preview.short_description = 'Motorcycle Photo'

    def license_photo_preview(self, obj):
        if obj.license_photo:
            return mark_safe(f'<img src="{obj.license_photo.url}" style="max-width:300px;max-height:200px;border-radius:8px;" />')
        return 'No photo uploaded'
    license_photo_preview.short_description = 'License Photo'

    def face_left_preview(self, obj):
        if obj.face_left:
            return mark_safe(f'<img src="{obj.face_left.url}" style="max-width:250px;max-height:250px;border-radius:8px;" />')
        return 'No photo uploaded'
    face_left_preview.short_description = '👈 Face Left'

    def face_front_preview(self, obj):
        if obj.face_front:
            return mark_safe(f'<img src="{obj.face_front.url}" style="max-width:250px;max-height:250px;border-radius:8px;" />')
        return 'No photo uploaded'
    face_front_preview.short_description = '😊 Face Front'

    def face_right_preview(self, obj):
        if obj.face_right:
            return mark_safe(f'<img src="{obj.face_right.url}" style="max-width:250px;max-height:250px;border-radius:8px;" />')
        return 'No photo uploaded'
    face_right_preview.short_description = '👉 Face Right'

    def approve_riders(self, request, queryset):
        updated = queryset.filter(user_type='delivery').update(is_active=True)
        self.message_user(request, f'{updated} rider(s) approved successfully.')
    approve_riders.short_description = '✓ Approve selected riders'

    def reject_riders(self, request, queryset):
        updated = queryset.filter(user_type='delivery').update(is_active=False)
        self.message_user(request, f'{updated} rider(s) rejected/deactivated.')
    reject_riders.short_description = '✗ Reject/Deactivate selected riders'
