from rest_framework import serializers
from booking.models import Booking
from garage.models import ParkingSpot, Garage
from django.db.models import Sum
from django.utils import timezone
import datetime

class BookingSerializer(serializers.ModelSerializer):
    driver_username = serializers.CharField(source='driver.username', read_only=True)
    spot_number = serializers.CharField(source='parking_spot.slot_number', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'driver_username', 'spot_number', 'start_time',
            'actual_cost', 'status', 'created_at'
        ]

class ParkingSpotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingSpot
        fields = ['id', 'slot_number', 'status']

class GarageDashboardSerializer(serializers.ModelSerializer):
    available_spots_count = serializers.SerializerMethodField()
    occupied_spots_count = serializers.SerializerMethodField()
    reserved_spots_count = serializers.SerializerMethodField()
    today_revenue = serializers.SerializerMethodField()
    today_bookings = serializers.SerializerMethodField()
    spots = ParkingSpotSerializer(many=True, read_only=True)
    is_open = serializers.SerializerMethodField()

    class Meta:
        model = Garage
        fields = [
            'id', 'name', 'address', 'price_per_hour',
            'opening_hour', 'closing_hour',  
            'available_spots_count', 'occupied_spots_count', 'reserved_spots_count',
            'today_revenue', 'today_bookings', 'spots','is_open'
        ]


    def get_is_open(self, obj):
        """
        Checks if the garage is currently open based on its opening and closing hours.
        """
        if not obj.opening_hour or not obj.closing_hour:
            return False

        current_time = timezone.localtime(timezone.now()).time()
        opening_hour = obj.opening_hour
        closing_hour = obj.closing_hour

        if opening_hour < closing_hour:
            return opening_hour <= current_time < closing_hour
        else:
            return current_time >= opening_hour or current_time < closing_hour


    def get_available_spots_count(self, obj):
        return obj.spots.filter(status='available').count()

    def get_occupied_spots_count(self, obj):
        return obj.spots.filter(status='occupied').count()

    def get_reserved_spots_count(self, obj):
        return obj.spots.filter(status='reserved').count()

    def get_today_revenue(self, obj):
        today = timezone.localdate()
        revenue = Booking.objects.filter(
            garage=obj,
            end_time__date=today,
            actual_cost__isnull=False
        ).aggregate(total_revenue=Sum('actual_cost'))['total_revenue']
        return revenue or 0.00

    def get_today_bookings(self, obj):
        today = timezone.localdate()
        bookings = Booking.objects.filter(
            garage=obj,
            created_at__date=today
        ).exclude(
            status__in=['cancelled', 'expired']
        ).order_by('-created_at')
        return BookingSerializer(bookings, many=True).data
