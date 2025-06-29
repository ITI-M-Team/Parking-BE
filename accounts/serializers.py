

from rest_framework import serializers
from .models import CustomUser
from django.contrib.auth.hashers import make_password
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
        user=self.user
        data['user']={
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "national_id": user.national_id,
            "phone": user.phone,
            "driver_license": user.driver_license.url if user.driver_license else None,
            "car_license": user.car_license.url if user.car_license else None,
            "national_id_img": user.national_id_img.url if user.national_id_img else None,
        }
        return data

        data['role'] = user.role
        return data

