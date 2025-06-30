

from rest_framework import serializers
from .models import CustomUser
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
