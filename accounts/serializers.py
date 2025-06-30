

from rest_framework import serializers
from .models import *
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

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
        validated_data['is_active'] = False

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
    username_field = CustomUser.EMAIL_FIELD

    def validate(self, attrs):
        credentials = {
            'email': attrs.get('email'),
            'password': attrs.get('password')
        }

        user = authenticate(**credentials)
        if user is None or not user.is_active:
            raise serializers.ValidationError("Account inactive or invalid credentials.")

        data = super().validate(attrs)

        if self.user.verification_status != 'Verified':
            raise serializers.ValidationError("Your account is not approved yet.")
        request = self.context.get('request')
        def build_url(file):
            if file:
                return request.build_absolute_uri(file.url) if request else file.url
            return None

        data['user']={
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "national_id": user.national_id,
            "phone": user.phone,
            "driver_license": build_url(user.driver_license),
            "car_license": build_url(user.car_license),
            "national_id_img": build_url(user.national_id_img),
        }
        return data

        data['role'] = user.role
        return data
##Update current user data
class UserUpdateSerializer(serializers.ModelSerializer):
    new_password = serializers.CharField(write_only=True, required=False)
    confirm_password = serializers.CharField(write_only=True, required=False)
    class Meta:
        model = CustomUser
        fields = [
                'email', 'username', 'phone', 'national_id',
                'driver_license', 'car_license', 'national_id_img',
                'new_password', 'confirm_password'
                ]
        #Can send without change nothing is requiered
        extra_kwargs = {
            'email': {'required': False},
            'username': {'required': False},
            'phone': {'required': False},
             'national_id': {'required': False},
            'driver_license': {'required': False},
            'car_license': {'required': False},
            'national_id_img': {'required': False},
        }
        ##Check the passwords first
    def validate(self, data):
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        if new_password or confirm_password:
            if new_password != confirm_password:
                raise serializers.ValidationError("Passwords do not match.")
            validate_password(new_password)
        return data
    ##Update and hash using set_password 
    def update(self, instance, validated_data):
        password = validated_data.pop('new_password', None)
        validated_data.pop('confirm_password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)
        instance.save()
        return instance
#####################################################################
###############
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
        method = data.get('method')
        email = data.get('email')
        phone = data.get('phone')

        if method == 'email' and not email:
            raise serializers.ValidationError("Email is required for email method.")
        if method == 'phone' and not phone:
            raise serializers.ValidationError("Phone is required for phone method.")

        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")

        return data
