# garage/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Garage, GarageReview, ParkingSpot

# Inline لإدارة ParkingSpot مباشرة من صفحة Garage
class ParkingSpotInline(admin.TabularInline):
    model = ParkingSpot
    extra = 1 # عدد الصفوف الفارغة لإضافة أماكن ركن جديدة

@admin.register(Garage)
class GarageAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'owner', 'address', 'price_per_hour',
        'total_spots_count', 'available_spots_count', 'preview_image' # <--- تم تصحيح القوس هنا
    )
    list_filter = ('owner', 'price_per_hour')
    search_fields = ('name', 'address', 'owner__email')
    inlines = [ParkingSpotInline] # هذا مهم جداً لإدارة أماكن الركن بسهولة

    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="75" />', obj.image.url)
        return "No Image"
    preview_image.short_description = 'Image'

    # دوال مخصصة لعرض عدد الأماكن (مفيدة جداً للـ owner_dashboard)
    def total_spots_count(self, obj):
        return obj.spots.count()
    total_spots_count.short_description = 'Total Spots'

    def available_spots_count(self, obj):
        return obj.spots.filter(status='available').count()
    available_spots_count.short_description = 'Available Spots'

@admin.register(GarageReview)
class GarageReviewAdmin(admin.ModelAdmin):
    list_display = ('garage', 'rating')
    list_filter = ('garage', 'rating')
    search_fields = ('garage__name',)

@admin.register(ParkingSpot)
class ParkingSpotAdmin(admin.ModelAdmin):
    list_display = ('garage', 'slot_number', 'status')
    list_filter = ('garage', 'status')
    search_fields = ('garage__name', 'slot_number')

