from rest_framework import serializers
from garage.models import ParkingSpot, Garage
from booking.models import Booking
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

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

    class Meta:
        model = Booking
        fields = [
            'id',
            'garage_name',
            'spot_id',
            'estimated_arrival_time',
            'estimated_cost',
            'reservation_expiry_time',
            'status',
            'qr_code_image',
            'wallet_balance'
        ]

    def get_wallet_balance(self, obj):
        return float(obj.driver.wallet_balance)