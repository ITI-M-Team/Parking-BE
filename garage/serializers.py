from rest_framework import serializers
from .models import Garage, GarageReview, ParkingSpot
from geopy.distance import geodesic

class GarageDetailSerializer(serializers.ModelSerializer):
    average_rating = serializers.SerializerMethodField()
    image = serializers.ImageField()

    def get_average_rating(self, obj):
        return getattr(obj, 'average_rating', None)  # From annotation
    class Meta:
        model = Garage
        fields = ['id', 'name', 'address', 'latitude', 'longitude',
                  'opening_hour', 'closing_hour', 'average_rating','image', 'price_per_hour','block_duration_hours']

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
    available_spots = serializers.SerializerMethodField()

    class Meta:
        model = Garage
        fields = ['id', 'name', 'address', 'latitude', 'longitude',
                  'price_per_hour', 'distance', 'available_spots']

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

    def get_available_spots(self, obj):
        return obj.spots.filter(status='available').count()

##########  grage registration serializer ##########
class GarageRegistrationSerializer(serializers.ModelSerializer):
    number_of_spots = serializers.IntegerField(write_only=True)

    class Meta:
        model = Garage
        fields = [
            'name', 'address', 'latitude', 'longitude',
            'opening_hour', 'closing_hour', 'image',
            'price_per_hour', 'number_of_spots','block_duration_hours','reservation_grace_period'
        ]

    def validate_number_of_spots(self, value):
        if value <= 0:
            raise serializers.ValidationError("Number of parking spots must be greater than 0.")
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        number_of_spots = validated_data.pop('number_of_spots')

        garage = Garage.objects.create(
            owner=request.user,  # ✅ Assign the logged-in user
            **validated_data
        )

        for i in range(1, number_of_spots + 1):
            ParkingSpot.objects.create(
                garage=garage,
                slot_number=f"SLOT-{i:03d}"
            )
        return garage

########## end grage registration serializer ##########
############## Garage Update Serializer ##########
# serializers.py
class GarageUpdateSerializer(serializers.ModelSerializer):
    number_of_spots = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Garage
        fields = [
            'name', 'address', 'latitude', 'longitude',
            'opening_hour', 'closing_hour', 'image',
            'price_per_hour', 'reservation_grace_period',
            'number_of_spots','block_duration_hours',
        ]

    def update(self, instance, validated_data):
        number_of_spots = validated_data.pop('number_of_spots', None)

        # ✅ Update all other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # ✅ Handle parking spots adjustment
        if number_of_spots is not None:
            current_count = instance.spots.count()

            if number_of_spots > current_count:
                for i in range(current_count + 1, number_of_spots + 1):
                    ParkingSpot.objects.create(
                        garage=instance,
                        slot_number=f"SLOT-{i:03d}"
                    )
            elif number_of_spots < current_count:
                # Only delete available spots (leave reserved/occupied untouched)
                removable_spots = list(
                    instance.spots.filter(status='available').order_by('-id')
                )
                to_delete = removable_spots[:current_count - number_of_spots]
                for spot in to_delete:
                    spot.delete()

        return instance

#################end Garage Update Serializer ##########

#########
class GarageReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = GarageReview
        fields = ['id', 'driver', 'garage', 'booking', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'driver', 'garage', 'created_at']

    def create(self, validated_data):
        validated_data['driver'] = self.context['request'].user
        validated_data['garage'] = self.context['garage']
        validated_data['booking'] = self.context['booking']
        return super().create(validated_data)
