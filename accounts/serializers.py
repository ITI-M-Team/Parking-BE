# from rest_framework import serializers

# from .models import CustomUser
# from django.contrib.auth.hashers import make_password


# class CustomUserSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True, min_length=8)
#     driver_license = serializers.FileField(required=False, allow_null=True)
#     car_license = serializers.FileField(required=False, allow_null=True)
#     national_id_img = serializers.FileField(required=False, allow_null=True)

#     class Meta:
#         model = CustomUser
#         fields = [
#             'id', 'username', 'email', 'phone', 'role', 'verification_status',
#             'national_id', 'driver_license', 'car_license', 'national_id_img'            
#         ]

#         read_only_fields=['id']

#     def create(self, validated_data):
#         # إزالة الملفات من البيانات الأساسية
#         driver_license = validated_data.pop('deiver_license', None)
#         car_license = validated_data.pop('car_license', None)
#         national_id_img = validated_data.pop('national_id_img', None)

#         # hash pass
#         validated_data['password'] = make_password(validated_data['password'])
#         validated_data['verification_status'] = 'Pending'
#         # HINT:
#         #     this equivalent to this :
#         # user = CustomUser()
#         # user.username = validated_data['username']
#         # user.email = validated_data['email']
#         # user.password = make_password(validated_data['password'])
#         # user.role = validated_data['role']
#         # user.national_id = validated_data['national_id']
#         # user.verification_status = 'Pending'
#         user = CustomUser.objects.create(**validated_data)

#         if driver_license:
#             user.driver_license = driver_license
#         if car_license:
#             user.car_license = car_license
#         if national_id_img:
#             user.national_id_img = national_id_img

#         user.save()
#         return user


from rest_framework import serializers
from .models import CustomUser
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Garage
from geopy.distance import geodesic

# from rest_framework_simplejwt.tokens import RefreshToken

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'phone', 'password', 'role',
            'national_id', 'driver_license', 'car_license', 'national_id_img'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'username': {'required': True},
            'phone': {'required': True},
            'national_id': {'required': True}
        }

    def create(self, validated_data):
        driver_license = validated_data.pop('driver_license', None)
        car_license = validated_data.pop('car_license', None)
        national_id_img = validated_data.pop('national_id_img', None)

        validated_data['password'] = make_password(validated_data['password'])
        validated_data['verification_status'] = 'Pending'

        user = CustomUser.objects.create(**validated_data)

        if driver_license:
            user.driver_license = driver_license
        if car_license:
            user.car_license = car_license
        if national_id_img:
            user.national_id_img = national_id_img

        user.save()
        return user
    


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.verification_status != 'Verified':
            raise serializers.ValidationError("Your account is not approved yet.")
        data['role'] = self.user.role
        return data
    



    # class NearbyGarageSerializer(serializers.ModelSerializer):
    
class GarageSerializer(serializers.ModelSerializer):
   
    distance = serializers.SerializerMethodField()

    class Meta:
        model = Garage
        fields = ['id', 'name', 'address', 'latitude', 'longitude',
                  'hourly_rate', 'available_spots', 'average_rating', 'distance']

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