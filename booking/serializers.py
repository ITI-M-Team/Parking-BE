from rest_framework import serializers
from garage.models import ParkingSpot, Garage

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
