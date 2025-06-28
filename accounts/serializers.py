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
#####################################################################
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False, max_length=15)
    method = serializers.CharField()

    def validate(self, data):
        method = data['method']
        if method == 'email' and not data.get('email'):
            raise serializers.ValidationError("Email is required for email method")
        if method == 'phone' and not data.get('phone'):
            raise serializers.ValidationError("Phone is required for phone method")
        
        # Validate Egyptian phone number format if phone is provided
        if method == 'phone' and data.get('phone'):
            phone = data['phone']
            if len(phone) != 11 or not phone.startswith(('010', '011', '012', '015')):
                raise serializers.ValidationError("Phone must be a valid Egyptian number")
        
        return data

class PasswordResetVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False, max_length=15)
    otp = serializers.CharField(max_length=6)
    method = serializers.CharField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False, max_length=15)
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8, max_length=128)
    confirm_password = serializers.CharField(min_length=8, max_length=128)
    method = serializers.CharField()

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        return data