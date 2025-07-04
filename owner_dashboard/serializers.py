
from rest_framework import serializers
from booking.models import Booking
from garage.models import ParkingSpot, Garage
from django.db.models import Sum, Count, Q

class ParkingSpotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingSpot
        fields = ['id', 'slot_number', 'status']

class BookingSerializer(serializers.ModelSerializer):
    parking_spot_slot_number = serializers.CharField(source='parking_spot.slot_number', read_only=True)
    driver_email = serializers.CharField(source='driver.email', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'driver_email', 'parking_spot_slot_number',
            'estimated_arrival_time', 'estimated_cost', 'status', 'created_at'
        ]

class GarageDashboardSerializer(serializers.ModelSerializer):
    # يمكنك إضافة حقول أخرى هنا إذا أردت عرض تفاصيل الجراج في لوحة التحكم
    # total_spots = serializers.SerializerMethodField() # إذا لم يكن لديك حقل total_spots في Garage model
    available_spots_count = serializers.SerializerMethodField()
    occupied_spots_count = serializers.SerializerMethodField()
    reserved_spots_count = serializers.SerializerMethodField()
    today_revenue = serializers.SerializerMethodField()
    today_bookings = serializers.SerializerMethodField()

    class Meta:
        model = Garage
        fields = [
            'id', 'name', 'address', 'latitude', 'longitude',
            'opening_hour', 'closing_hour', 'price_per_hour',
            'available_spots_count', 'occupied_spots_count', 'reserved_spots_count',
            'today_revenue', 'today_bookings'
        ]

    # إذا لم يكن لديك حقل total_spots في Garage model
    # def get_total_spots(self, obj):
    #     return obj.spots.count()

    def get_available_spots_count(self, obj):
        return obj.spots.filter(status='available').count()

    def get_occupied_spots_count(self, obj):
        return obj.spots.filter(status='occupied').count()

    def get_reserved_spots_count(self, obj):
        return obj.spots.filter(status='reserved').count()

    def get_today_revenue(self, obj):
        # يحسب الإيرادات من الحجوزات المؤكدة التي تمت اليوم
        today = timezone.localdate()
        revenue = Booking.objects.filter(
            garage=obj,
            status='confirmed',
            created_at__date=today
        ).aggregate(total_revenue=Sum('estimated_cost'))['total_revenue']
        return revenue if revenue is not None else 0.0

    def get_today_bookings(self, obj):
        # يجلب الحجوزات المؤكدة والمنتظرة لليوم
        today = timezone.localdate()
        bookings = Booking.objects.filter(
            garage=obj,
            created_at__date=today
        ).exclude(status='cancelled').order_by('-created_at')
        return BookingSerializer(bookings, many=True).data

