from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta
import random

class User(AbstractUser):
    USER_TYPE_CHOICES = [
        ('customer', 'Customer'),
        ('store_admin', 'Store Admin'),
        ('delivery', 'Delivery Rider'),
    ]
    
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='customer')
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery Rider specific fields
    motorcycle_color = models.CharField(max_length=50, blank=True)
    plate_number = models.CharField(max_length=20, blank=True)
    driver_license = models.CharField(max_length=50, blank=True)
    motorcycle_photo = models.ImageField(upload_to='rider_docs/', null=True, blank=True)
    license_photo = models.ImageField(upload_to='rider_docs/', null=True, blank=True)
    face_left = models.ImageField(upload_to='rider_docs/', null=True, blank=True)
    face_front = models.ImageField(upload_to='rider_docs/', null=True, blank=True)
    face_right = models.ImageField(upload_to='rider_docs/', null=True, blank=True)
    push_token = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return f"{self.username} - {self.get_full_name() or self.email}"
    
    def generate_otp(self):
        self.otp_code = str(random.randint(100000, 999999))
        self.otp_expires_at = timezone.now() + timedelta(minutes=10)
        self.save(update_fields=['otp_code', 'otp_expires_at'])
        return self.otp_code

    def verify_otp(self, code):
        if not self.otp_code or not self.otp_expires_at:
            return False
        if timezone.now() > self.otp_expires_at:
            return False
        return self.otp_code == str(code)

    def is_account_locked(self):
        if self.account_locked_until and timezone.now() < self.account_locked_until:
            return True
        return False
    
    def increment_failed_login(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.account_locked_until = timezone.now() + timedelta(minutes=15)
        self.save()
    
    def reset_failed_login(self):
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.save()
