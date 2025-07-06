from rest_framework import serializers
from .models import Booking
from garage.models import Garage, ParkingSpot


class BookingInitiationSerializer(serializers.Serializer):
    garage_id = serializers.IntegerField()
    parking_spot_id = serializers.IntegerField()
    estimated_arrival_time = serializers.DateTimeField()

    def validate(self, data):
        garage_id = data.get('garage_id')
        spot_id = data.get('parking_spot_id')

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

        self.garage = garage
        self.spot = spot
        return data


class BookingDetailSerializer(serializers.ModelSerializer):
    garage_name = serializers.CharField(source='garage.name', read_only=True)
    spot_id = serializers.IntegerField(source='parking_spot.id', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'garage_name', 'spot_id',
            'estimated_arrival_time', 'estimated_cost',
            'reservation_expiry_time', 'status',
            'qr_code_image'
        ]
