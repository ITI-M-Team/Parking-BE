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
        estimated_time = data.get("estimated_arrival_time")

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

        dummy_user = User.objects.first()
        grace_period = garage.reservation_grace_period
        expiry_time = estimated_time + timedelta(minutes=grace_period)

        overlapping_booking = Booking.objects.filter(
            driver=dummy_user,
            status__in=["pending", "confirmed"],
            estimated_arrival_time__lt=expiry_time,
            reservation_expiry_time__gt=estimated_time
        ).exists()

        if overlapping_booking:
            raise serializers.ValidationError("You already have a booking during this time window.")

        data['garage'] = garage
        data['spot'] = spot
        return data

class BookingDetailSerializer(serializers.ModelSerializer):
    garage = serializers.SerializerMethodField()
    parking_spot = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'garage', 'parking_spot',
            'estimated_arrival_time',
            'reservation_expiry_time', 'status',
            'qr_code_image'
        ]

    def get_garage(self, obj):
        return {
            "id": obj.garage.id,
            "name": obj.garage.name
        }

    def get_parking_spot(self, obj):
        return {
            "id": obj.parking_spot.id,
            "slot_number": obj.parking_spot.slot_number
        }
