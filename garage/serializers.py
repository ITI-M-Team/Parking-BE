from rest_framework import serializers
from .models import Garage, ParkingSpot


class GarageDetailSerializer(serializers.ModelSerializer):
    average_rating = serializers.FloatField()

    class Meta:
        model = Garage
        fields = ['id', 'name', 'address', 'latitude', 'longitude',
                  'opening_hour', 'closing_hour', 'average_rating']



class ParkingSpotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingSpot
        fields = ['id', 'slot_number', 'status']