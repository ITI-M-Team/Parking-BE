from django.contrib import admin
from django.utils.html import format_html
from .models import Garage, GarageReview, ParkingSpot

class GarageAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'price_per_hour', 'preview_image')

    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="75" />', obj.image.url)
        return "No Image"

    preview_image.short_description = 'Image'

admin.site.register(Garage, GarageAdmin)
admin.site.register(GarageReview)
admin.site.register(ParkingSpot)
