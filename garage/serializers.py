from rest_framework import serializers
from .models import Garage, GarageReview, GarageVerificationRequest, ParkingSpot
from geopy.distance import geodesic

class GarageDetailSerializer(serializers.ModelSerializer):
    average_rating = serializers.SerializerMethodField()
    image = serializers.ImageField()
    contract_document = serializers.FileField() 
    def get_average_rating(self, obj):
        return getattr(obj, 'average_rating', None)  # From annotation
    class Meta:
        model = Garage
        fields = ['id', 'name', 'address', 'latitude', 'longitude',
            'opening_hour', 'closing_hour', 'average_rating', 'image', 
            'price_per_hour', 'block_duration_hours', 'reservation_grace_period',
            'verification_status','contract_document',
      ]

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
                  'price_per_hour', 'distance', 'available_spots', 'verification_status']

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
    contract_document = serializers.FileField(required=True)
    class Meta:
        model = Garage
        fields = [
            'name', 'address', 'latitude', 'longitude',
            'opening_hour', 'closing_hour', 'image',
            'price_per_hour', 'number_of_spots', 'block_duration_hours',
            'reservation_grace_period', 'contract_document'  
        ]

    def validate_number_of_spots(self, value):
        if value <= 0:
            raise serializers.ValidationError("Number of parking spots must be greater than 0.")
        return value
    # #######Validate contract document file type and size
    def validate_contract_document(self, value):
        if not value:
            raise serializers.ValidationError("Contract document is required.")
        
        # Check file extension
        allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
        file_extension = value.name.lower().split('.')[-1]
        if f'.{file_extension}' not in allowed_extensions:
            raise serializers.ValidationError(
                "Only PDF, DOC, DOCX, JPG, JPEG, and PNG files are allowed for contract documents."
            )
        
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError(
                "Contract document size cannot exceed 10MB."
            )
        
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        number_of_spots = validated_data.pop('number_of_spots')

        garage = Garage.objects.create(
            owner=request.user,  # ✅ Assign the logged-in user
            verification_status='Pending',  # Always start as Pending
            **validated_data
        )

        for i in range(1, number_of_spots + 1):
            ParkingSpot.objects.create(
                garage=garage,
                slot_number=f"SLOT-{i:03d}"
            )
        # Create verification request
        GarageVerificationRequest.objects.create(
            garage=garage,
            status='Pending'
        )
        return garage

########## end grage registration serializer ##########
############## Garage Update Serializer ##########
# serializers.py
class GarageUpdateSerializer(serializers.ModelSerializer):
    number_of_spots = serializers.IntegerField(write_only=True, required=False)
    contract_document = serializers.FileField(required=False)
    class Meta:
        model = Garage
        fields = [
            'name', 'address', 'latitude', 'longitude',
            'opening_hour', 'closing_hour', 'image',
            'price_per_hour', 'reservation_grace_period',
            'number_of_spots','block_duration_hours',
            'contract_document'
        ]

        #### Validate contract document file type and size (for updates)
    def validate_contract_document(self, value):
        
        if value:  # Only validate if a new file is uploaded
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
            file_extension = value.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise serializers.ValidationError(
                    "Only PDF, DOC, DOCX, JPG, JPEG, and PNG files are allowed for contract documents."
                )
            
            # Check file size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB in bytes
            if value.size > max_size:
                raise serializers.ValidationError(
                    "Contract document size cannot exceed 10MB."
                )
        
        return value
    
    def update(self, instance, validated_data):
        number_of_spots = validated_data.pop('number_of_spots', None)

         # Check if critical fields are being updated (requires re-verification)
        critical_fields = ['contract_document', 'name', 'address', 'latitude', 'longitude']
        needs_reverification = any(field in validated_data for field in critical_fields)
        # ✅ Update all other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
         # If critical fields changed, reset to Pending and create new verification request
        if needs_reverification:
            instance.verification_status = 'Pending'
            GarageVerificationRequest.objects.create(
                garage=instance,
                status='Pending'
            )
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
# New serializer for garage verification requests
class GarageVerificationRequestSerializer(serializers.ModelSerializer):
    garage_name = serializers.CharField(source='garage.name', read_only=True)
    garage_address = serializers.CharField(source='garage.address', read_only=True)
    garage_image = serializers.SerializerMethodField()
    garage_contract_document = serializers.SerializerMethodField()
    garage_price_per_hour = serializers.DecimalField(source='garage.price_per_hour', max_digits=10, decimal_places=2, read_only=True)
    garage_latitude = serializers.FloatField(source='garage.latitude', read_only=True)
    garage_longitude = serializers.FloatField(source='garage.longitude', read_only=True)
    garage_opening_hour = serializers.TimeField(source='garage.opening_hour', read_only=True)
    garage_closing_hour = serializers.TimeField(source='garage.closing_hour', read_only=True)
    
    owner_email = serializers.CharField(source='garage.owner.email', read_only=True)
    owner_username = serializers.CharField(source='garage.owner.username', read_only=True)
    owner_first_name = serializers.CharField(source='garage.owner.first_name', read_only=True)
    owner_last_name = serializers.CharField(source='garage.owner.last_name', read_only=True)
    owner_phone = serializers.CharField(source='garage.owner.phone', read_only=True)
    owner_name = serializers.SerializerMethodField()
    
    total_spots = serializers.SerializerMethodField()
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True)
    
    # Add garage nested data
    garage = serializers.SerializerMethodField()
    
    class Meta:
        model = GarageVerificationRequest
        fields = [
            'id', 'garage', 'garage_name', 'garage_address', 'garage_image', 
            'garage_contract_document', 'garage_price_per_hour',
            'garage_latitude', 'garage_longitude', 'garage_opening_hour', 'garage_closing_hour',
            'owner_email', 'owner_username', 'owner_first_name', 'owner_last_name', 
            'owner_phone', 'owner_name', 'total_spots',
            'status', 'reason', 'reviewed_by', 'reviewed_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_owner_name(self, obj):
        if obj.garage and obj.garage.owner:
            full_name = f"{obj.garage.owner.first_name} {obj.garage.owner.last_name}".strip()
            return full_name if full_name else obj.garage.owner.username
        return 'Unknown'
    
    def get_total_spots(self, obj):
        if obj.garage:
            return obj.garage.spots.count()
        return 0
    
    def get_garage_image(self, obj):
        if obj.garage and obj.garage.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.garage.image.url)
            return obj.garage.image.url
        return None
    
    def get_garage_contract_document(self, obj):
        if obj.garage and obj.garage.contract_document:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.garage.contract_document.url)
            return obj.garage.contract_document.url
        return None
    
    def get_garage(self, obj):
        """Return garage data in the expected format for frontend"""
        if not obj.garage:
            return None
            
        garage = obj.garage
        request = self.context.get('request')
        
        return {
            'id': garage.id,
            'name': garage.name,
            'address': garage.address,
            'latitude': garage.latitude,
            'longitude': garage.longitude,
            'price_per_hour': str(garage.price_per_hour),
            'opening_hour': garage.opening_hour,
            'closing_hour': garage.closing_hour,
            'verification_status': garage.verification_status,
            'image': request.build_absolute_uri(garage.image.url) if garage.image and request else None,
            'contract_document': request.build_absolute_uri(garage.contract_document.url) if garage.contract_document and request else None,
            'total_spots': garage.spots.count(),
            'owner': {
                'id': garage.owner.id,
                'username': garage.owner.username,
                'email': garage.owner.email,
                'first_name': garage.owner.first_name,
                'last_name': garage.owner.last_name,
                'phone': getattr(garage.owner, 'phone', None),
            }
        }
# Serializer for admin actions on garage verification
class GarageVerificationActionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=GarageVerificationRequest.STATUS_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True)

#########
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