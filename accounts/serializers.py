from rest_framework import serializers
from django.core.mail import send_mail
from django.conf import settings
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
        }

    # Email validation
    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    # Username validation
    def validate_username(self, value):
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    # Phone validation
    def validate_phone(self, value):
        if not value.isdigit() or len(value) != 11 or not value.startswith(('010', '011', '012', '015')):
            raise serializers.ValidationError("Enter a valid Egyptian phone number.")
        if CustomUser.objects.filter(phone=value).exists():
            raise serializers.ValidationError("This phone number is already in use.")
        return value

    # National ID validation
    def validate_national_id(self, value):
        if not value.isdigit() or len(value) != 14:
            raise serializers.ValidationError("Enter a valid 14-digit national ID.")
        if CustomUser.objects.filter(national_id=value).exists():
            raise serializers.ValidationError("This national ID is already registered.")
        return value
    

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
        #### Create verification request if documents are uploaded  ####
        if user.has_documents:
            VerificationRequest.objects.create(user=user)
        return user
# Custom Token Obtain Pair Serializer
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = CustomUser.EMAIL_FIELD

    def validate(self, attrs):
        credentials = {
            # 'email': attrs.get('email'),
            self.username_field: attrs.get(self.username_field),
            'password': attrs.get('password')
        }

        user = authenticate(**credentials)
        if user is None or not user.is_active:
            raise serializers.ValidationError("Account inactive or invalid credentials.")

        data = super().validate(attrs)

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
            "is_superuser": user.is_superuser,
            "is_staff": user.is_staff,
        }
        return data

        data['role'] = user.role
        return data


# User Update Serializer
class UserUpdateSerializer(serializers.ModelSerializer):
    new_password = serializers.CharField(write_only=True, required=False)
    confirm_password = serializers.CharField(write_only=True, required=False)
    resubmission = serializers.CharField(write_only=True, required=False)
    class Meta:
        model = CustomUser
        
        fields = [
            'email', 'username', 'phone', 'national_id',
            'driver_license', 'car_license', 'national_id_img',
            'profile_image','new_password', 'confirm_password', 'resubmission'
        ]
        extra_kwargs = {
            'email': {'required': False},
            'username': {'required': False},
            'phone': {'required': False},
            'national_id': {'required': False},
            'driver_license': {'required': False},
            'car_license': {'required': False},
            'national_id_img': {'required': False},
            'profile_image': {'required': False},
        }

    def validate(self, data):
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        if new_password or confirm_password:
            if new_password != confirm_password:
                raise serializers.ValidationError("Passwords do not match.")
            validate_password(new_password)
        return data
    

### Check for new Documents !
    def _has_new_documents(self, validated_data):
        document_fields = ['driver_license', 'car_license', 'national_id_img']
        return any(field in validated_data for field in document_fields)
    
#### Check if this is a resubmission after rejection
    def _is_resubmission(self, validated_data):
        return validated_data.get('resubmission') == 'true'
    
    def update(self, instance, validated_data):
        password = validated_data.pop('new_password', None)
        validated_data.pop('confirm_password', None)
        is_resubmission = self._is_resubmission(validated_data)
        validated_data.pop('resubmission', None) 
    ##### Check if new documents are being uploaded ####

        old_has_documents = instance.has_documents
        old_verification_status = instance.verification_status
        has_new_documents = self._has_new_documents(validated_data)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        
        # Handle verification status changes

        if has_new_documents:
            if is_resubmission and old_verification_status == 'Rejected':
                instance.verification_status = 'Pending'
                self._handle_resubmission(instance)
            elif not old_has_documents or old_verification_status != 'Pending':
                instance.verification_status = 'Pending'
                self._create_verification_request(instance)
        instance.save()
        return instance
    
#-----  Handle resubmission of documents after rejection  -----#

    def _handle_resubmission(self, instance):
        try:
            rejected_request = VerificationRequest.objects.filter(
                user=instance,
                status='Rejected'
            ).order_by('-updated_at').first()
            
            if rejected_request:
                rejected_request.status = 'Pending'
                rejected_request.reason = ''  
                rejected_request.reviewed_by = None  
                rejected_request.save()
            else:
                self._create_verification_request(instance)
        except Exception as e:
            self._create_verification_request(instance)

#-----  Create a new verification request  -----#

    def _create_verification_request(self, instance):
        if not VerificationRequest.objects.filter(user=instance, status='Pending').exists():
            VerificationRequest.objects.create(user=instance)


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
#### verification Request Serializers to validate all user's data 

class VerificationRequestSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    user_national_id = serializers.CharField(source='user.national_id', read_only=True)
    user_driver_license = serializers.FileField(source='user.driver_license', read_only=True)
    user_car_license = serializers.FileField(source='user.car_license', read_only=True)
    user_national_id_img = serializers.FileField(source='user.national_id_img', read_only=True)
    user_profile_image = serializers.ImageField(source='user.profile_image', read_only=True)
    reviewed_by_username = serializers.CharField(source='reviewed_by.username', read_only=True)
    missing_documents = serializers.ListField(source='user.missing_documents', read_only=True)
    is_resubmission = serializers.SerializerMethodField()
    class Meta:
        model = VerificationRequest
        fields = [
            'id', 'user', 'status', 'reason', 'reviewed_by', 'created_at', 'updated_at',
            'user_email', 'user_username', 'user_phone', 'user_role', 'user_national_id',
            'user_driver_license', 'user_car_license', 'user_national_id_img', 'user_profile_image',
            'reviewed_by_username', 'missing_documents', 'is_resubmission'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
        
### Check if this is a resubmission (had a previous rejection)  ###
    def get_is_resubmission(self, obj):
        return VerificationRequest.objects.filter(
            user=obj.user,
            status='Rejected',
            created_at__lt=obj.created_at
        ).exists()
    
### Assign the varification status to the documents and validate it

class VerificationActionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['Pending', 'Verified', 'Rejected'])
    reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        if data['status'] == 'Rejected' and not data.get('reason'):
            raise serializers.ValidationError("Reason is required when rejecting a verification request.")
        return data

