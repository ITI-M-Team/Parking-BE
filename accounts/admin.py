from django.contrib import admin
from .models import CustomUser  # أضف Garage هنا

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'phone', 'role', 'verification_status']
    list_filter = ['role', 'verification_status']
    search_fields = ['username', 'email', 'phone', 'national_id']

