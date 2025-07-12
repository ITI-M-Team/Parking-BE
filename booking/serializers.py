from rest_framework import serializers
from garage.models import ParkingSpot, Garage
from booking.models import Booking
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from garage.serializers import GarageSerializer, ParkingSpotSerializer

User = get_user_model()

class BookingInitiationSerializer(serializers.Serializer):
    garage_id = serializers.IntegerField()
    parking_spot_id = serializers.IntegerField()
    estimated_arrival_time = serializers.DateTimeField()

    def validate(self, data):
        garage_id = data.get('garage_id')
        spot_id = data.get('parking_spot_id')
        estimated_time = data.get('estimated_arrival_time')

        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError({"detail": "Authentication required."})

        user = request.user

        try:
            garage = Garage.objects.get(id=garage_id)
        except Garage.DoesNotExist:
            raise serializers.ValidationError({"garage_id": "Garage not found."})

        try:
            spot = ParkingSpot.objects.get(id=spot_id, garage=garage)
        except ParkingSpot.DoesNotExist:
            raise serializers.ValidationError({"parking_spot_id": "Parking spot not found in this garage."})

        if spot.status != 'available':
            raise serializers.ValidationError({"parking_spot_id": "This parking spot is not available."})

        grace_period = garage.reservation_grace_period
        expiry_time = estimated_time + timedelta(minutes=grace_period)

        overlapping_booking = Booking.objects.filter(
            driver=user,
            status__in=["pending", "confirmed"],
            estimated_arrival_time__lt=expiry_time,
            reservation_expiry_time__gt=estimated_time
        ).exists()

        if overlapping_booking:
            raise serializers.ValidationError({
                "non_field_errors": ["You already have a conflicting booking."]
            })

        data['garage'] = garage
        data['spot'] = spot
        data['grace_period'] = grace_period
        data['estimated_cost'] = garage.price_per_hour

        return data


class BookingDetailSerializer(serializers.ModelSerializer):
    garage_name = serializers.CharField(source='garage.name', read_only=True)
    spot_id = serializers.IntegerField(source='parking_spot.id', read_only=True)
    wallet_balance = serializers.SerializerMethodField()
    parking_spot = serializers.CharField(source='parking_spot.slot_number', read_only=True)
    price_per_hour = serializers.DecimalField(source='garage.price_per_hour', max_digits=6, decimal_places=2, read_only=True)
    actual_cost = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True, allow_null=True, required=False)
    start_time = serializers.DateTimeField(read_only=True, allow_null=True, required=False)
    end_time = serializers.DateTimeField(read_only=True, allow_null=True, required=False)
    total_duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id',
            'garage',
            'garage_name',
            'parking_spot',
            'spot_id',
            'estimated_arrival_time',
            'estimated_cost',
            'reservation_expiry_time',
            'status',
            'qr_code_image',
            'wallet_balance',
            'price_per_hour',
            'start_time',
            'end_time',
            'actual_cost',
            'total_duration_minutes'
        ]

    def get_wallet_balance(self, obj):
        return float(obj.driver.wallet_balance)
    
    def get_total_duration_minutes(self, obj):
        if obj.start_time and obj.end_time:
            delta = obj.end_time - obj.start_time
            return int(delta.total_seconds() / 60)
        return None
        
    def get_actual_cost(self, obj):
        if obj.actual_cost is not None:
            return round(obj.actual_cost, 2)
        return None
