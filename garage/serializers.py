from rest_framework import serializers

from .models import Garage, ParkingSpot
from geopy.distance import geodesic



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






class GarageSerializer(serializers.ModelSerializer):
    distance = serializers.SerializerMethodField()

    class Meta:
        model = Garage
        fields = ['id', 'name', 'address', 'latitude', 'longitude',
                  'price_per_hour',  'distance']

    def get_distance(self, obj):
        request = self.context.get('request')
        if request:
            lat = request.query_params.get('lat')
            lon = request.query_params.get('lon')
            if lat and lon:
                return round(geodesic(
                    (float(lat), float(lon)),
                    (obj.latitude, obj.longitude)
                ).km, 2)
        return None
class GarageRegistrationSerializer(serializers.ModelSerializer):
    number_of_spots = serializers.IntegerField(write_only=True)

    class Meta:
        model = Garage
        fields = [
            'name', 'address', 'latitude', 'longitude',
            'opening_hour', 'closing_hour', 'image',
            'price_per_hour', 'number_of_spots'
        ]

    def validate_number_of_spots(self, value):
        if value <= 0:
            raise serializers.ValidationError("Number of parking spots must be greater than 0.")
        return value

    def create(self, validated_data):
        number_of_spots = validated_data.pop('number_of_spots')
        garage = Garage.objects.create(**validated_data)

        for i in range(1, number_of_spots + 1):
            ParkingSpot.objects.create(
                garage=garage,
                slot_number=f"SLOT-{i:03d}"
            )
        return garage
