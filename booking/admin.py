
from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'driver', 'garage', 'parking_spot', 'estimated_arrival_time', 'status')
    list_filter = ('status', 'garage')
    search_fields = ('driver__email', 'garage__name', 'parking_spot__slot_number')
