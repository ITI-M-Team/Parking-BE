from rest_framework import serializers
from .models import Garage, ParkingSpot


class GarageDetailSerializer(serializers.ModelSerializer):
    average_rating = serializers.FloatField()
    image = serializers.ImageField() 

    class Meta:
        model = Garage
        fields = ['id', 'name', 'address', 'latitude', 'longitude',
                  'opening_hour', 'closing_hour', 'average_rating','image', 'price_per_hour']
    
    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None


class ParkingSpotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingSpot
        fields = ['id', 'slot_number', 'status']