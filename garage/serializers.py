from rest_framework import serializers
from geopy.distance import geodesic
from .models import Garage, ParkingSpot


class GarageDetailSerializer(serializers.ModelSerializer):
    average_rating = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Garage
        fields = [
            'id', 'name', 'address', 'latitude', 'longitude',
            'opening_hour', 'closing_hour', 'average_rating',
            'image', 'price_per_hour'
        ]

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None

    def get_average_rating(self, obj):
        return getattr(obj, 'avg_rating', obj.average_rating)


class ParkingSpotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingSpot
        fields = ['id', 'slot_number', 'status']


class GarageSerializer(serializers.ModelSerializer):
    distance = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Garage
        fields = ['id', 'name', 'address', 'latitude', 'longitude',
                  'price_per_hour', 'distance', 'average_rating']

    def get_distance(self, obj):
        request = self.context.get('request')
        if request:
            lat = request.query_params.get('lat')
            lon = request.query_params.get('lon')
            if lat and lon:
                return round(geodesic((float(lat), float(lon)), (obj.latitude, obj.longitude)).km, 2)
        return None

    def get_average_rating(self, obj):
        return getattr(obj, 'avg_rating', obj.average_rating)


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
        request = self.context.get('request')
        number_of_spots = validated_data.pop('number_of_spots')

        garage = Garage.objects.create(owner=request.user, **validated_data)

        for i in range(1, number_of_spots + 1):
            ParkingSpot.objects.create(
                garage=garage,
                slot_number=f"SLOT-{i:03d}"
            )
        return garage


class GarageUpdateSerializer(serializers.ModelSerializer):
    number_of_spots = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Garage
        fields = [
            'name', 'address', 'latitude', 'longitude',
            'opening_hour', 'closing_hour', 'image',
            'price_per_hour', 'reservation_grace_period',
            'number_of_spots',
        ]

    def update(self, instance, validated_data):
        number_of_spots = validated_data.pop('number_of_spots', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if number_of_spots is not None:
            current_count = instance.spots.count()

            if number_of_spots > current_count:
                for i in range(current_count + 1, number_of_spots + 1):
                    ParkingSpot.objects.create(
                        garage=instance,
                        slot_number=f"SLOT-{i:03d}"
                    )
            elif number_of_spots < current_count:
                removable_spots = list(instance.spots.filter(status='available').order_by('-id'))
                to_delete = removable_spots[:current_count - number_of_spots]
                for spot in to_delete:
                    spot.delete()

        return instance
