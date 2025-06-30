from django.contrib import admin
from .models import CustomUser, Garage  # أضف Garage هنا

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'phone', 'role', 'verification_status']
    list_filter = ['role', 'verification_status']
    search_fields = ['username', 'email', 'phone', 'national_id']

@admin.register(Garage)  
class GarageAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'latitude', 'longitude', 'hourly_rate', 'available_spots', 'average_rating']
    search_fields = ['name', 'address']
