# from django.shortcuts import render
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.parsers import MultiPartParser, FormParser
# from .serializers import CustomUserSerializer

# # Create your views here.

# class RegisterView(APIView):
#     parser_classes = [MultiPartParser, FormParser]

#     def post(self, request, *args, **kwargs):
#         serializer = CustomUserSerializer(data=request.data)
#         if serializer.is_valid():
#             user = serializer.save()
#             return Response({
#                 "message": "Registration successful",
#                 "user_id": user.id
#             }, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#############################################
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from .models import CustomUser
from .serializers import RegisterSerializer , CustomTokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
# from rest_framework_simplejwt.tokens import RefreshToken

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    def perform_create(self, serializer):
        driver_license = serializer.validated_data.pop('driver_license', None)
        car_license = serializer.validated_data.pop('car_license', None)
        national_id_img = serializer.validated_data.pop('national_id_img', None)

        validated_data = serializer.validated_data
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




class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    
###########################################################
class PasswordResetRequestView(generics.CreateAPIView):
    serializer_class = PasswordResetRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        method = serializer.validated_data['method']
        email = serializer.validated_data.get('email')
        phone = serializer.validated_data.get('phone')
        
        try:
            if method == 'email':
                user = CustomUser.objects.get(email=email)
            else:
                user = CustomUser.objects.get(phone=phone)
        except CustomUser.DoesNotExist:
            # Return generic response to prevent user enumeration
            return Response(
                {"detail": "If this account exists, you'll receive an OTP"},
                status=status.HTTP_200_OK
            )

        # Create new OTP
        otp = PasswordResetOTP.create_for_user(user, method)
        
        if method == 'email':
            try:
                otp.send_otp_email()
            except Exception as e:
                return Response(
                    {"detail": "Failed to send OTP email"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # For phone/SMS, you would implement similar logic with your SMS provider
        # This is just a placeholder for demonstration
        if method == 'phone':
            print(f"OTP for {phone}: {otp.otp}")  # In production, send via SMS gateway
        
        return Response(
            {"detail": "OTP has been sent"},
            status=status.HTTP_200_OK
        )

class PasswordResetVerifyView(generics.CreateAPIView):
    serializer_class = PasswordResetVerifySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        method = serializer.validated_data['method']
        otp = serializer.validated_data['otp']
        email = serializer.validated_data.get('email')
        phone = serializer.validated_data.get('phone')
        
        try:
            if method == 'email':
                user = CustomUser.objects.get(email=email)
            else:
                user = CustomUser.objects.get(phone=phone)
                
            otp_record = PasswordResetOTP.objects.get(
                user=user,
                otp=otp,
                method=method,
                used=False
            )
        except (CustomUser.DoesNotExist, PasswordResetOTP.DoesNotExist):
            return Response(
                {"detail": "Invalid OTP or user"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not otp_record.is_valid():
            return Response(
                {"detail": "OTP has expired"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(
            {"detail": "OTP is valid"},
            status=status.HTTP_200_OK
        )

class PasswordResetConfirmView(generics.CreateAPIView):
    serializer_class = PasswordResetConfirmSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        method = serializer.validated_data['method']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']
        email = serializer.validated_data.get('email')
        phone = serializer.validated_data.get('phone')
        
        try:
            if method == 'email':
                user = CustomUser.objects.get(email=email)
            else:
                user = CustomUser.objects.get(phone=phone)
                
            otp_record = PasswordResetOTP.objects.get(
                user=user,
                otp=otp,
                method=method,
                used=False
            )
        except (CustomUser.DoesNotExist, PasswordResetOTP.DoesNotExist):
            return Response(
                {"detail": "Invalid OTP or user"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not otp_record.is_valid():
            return Response(
                {"detail": "OTP has expired"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update password
        user.set_password(new_password)
        user.save()
        
        # Mark OTP as used
        otp_record.used = True
        otp_record.save()
        
        return Response(
            {"detail": "Password has been reset successfully"},
            status=status.HTTP_200_OK
        )


