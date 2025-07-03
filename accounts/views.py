from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.conf import settings
from django.db.models import Q

from .models import *
from rest_framework.views import APIView
from .serializers import *
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode


from rest_framework_simplejwt.views import TokenObtainPairView


# Register View + Activation Email
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def perform_create(self, serializer):
        # user = serializer.save(commit=False) ##Commit parameter only used in Django Forms Not at Rest_Frame_Work !!
        user = serializer.save()
        user.is_active = False
        user.save()

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        activation_link = f"http://localhost:8000/api/activate/{uid}/{token}/"

        send_mail(
            'Activate your account',
            f'Click the link to activate your account: {activation_link}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
 

# Activate User View
class ActivateUserView(APIView):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)

            if user.is_active:
                return redirect(f"{settings.FRONTEND_BASE_URL}/activation?status=already-activated")

            if default_token_generator.check_token(user, token):
                user.is_active = True
                user.save()
                return redirect(f"{settings.FRONTEND_BASE_URL}/activation?status=success")
            else:
               return redirect(f"{settings.FRONTEND_BASE_URL}/activation?status=invalid-token")

        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return redirect(f"{settings.FRONTEND_BASE_URL}/activation?status=invalid-link")

# class ActivateUserView(APIView):
#     def get(self, request, uidb64, token):
#         try:
#             uid = force_str(urlsafe_base64_decode(uidb64))
#             user = CustomUser.objects.get(pk=uid)

#             if user.is_active:
#                 return Response({'message': 'Account already activated.'})

#             if default_token_generator.check_token(user, token):
#                 user.is_active = True
#                 user.save()
#                 return Response({'message': 'Account activated successfully.'}, status=200)
#             else:
#                 return Response({'error': 'Invalid activation token.'}, status=400)

#         except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
#             return Response({'error': 'Invalid activation link.'}, status=400)        


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

# Get/Update Current User View
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        user = request.user

        def build_url(file):
            return request.build_absolute_uri(file.url) if file else None

        return Response({
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "national_id": user.national_id,
            "phone": user.phone,
            "driver_license": build_url(user.driver_license),
            "car_license": build_url(user.car_license),
            "national_id_img": build_url(user.national_id_img),
        })

    def put(self, request):
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Profile updated successfully'})
        return Response(serializer.errors, status=400)



###########################################################
class PasswordResetRequestView(generics.CreateAPIView):
    serializer_class = PasswordResetRequestSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        method = serializer.validated_data['method']
        email = serializer.validated_data.get('email')
        phone = serializer.validated_data.get('phone')

        # Get user
        try:
            user = CustomUser.objects.get(email=email) if method == 'email' else CustomUser.objects.get(phone=phone)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "If this account exists, you'll receive an OTP."},
                status=status.HTTP_200_OK
            )

        try:
            # Create OTP
            otp = PasswordResetOTP.create_for_user(user, method)

            # Send OTP
            if method == 'email':
                subject = "Your Parking App Password Reset OTP"
                message = f"Your OTP code is: {otp.otp}\nThis code expires in 15 minutes."
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
            elif method == 'phone':
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                message = client.messages.create(
                    from_=settings.TWILIO_WHATSAPP_NUMBER,
                    to=f'whatsapp:+2{user.phone}',  # Egypt number
                    body=f"Your Parking App OTP is: {otp.otp}\nThis code expires in 15 minutes."
                )

            return Response({"detail": "OTP has been sent"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"detail": f"Failed to send OTP: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
            user = CustomUser.objects.get(email=email) if method == 'email' else CustomUser.objects.get(phone=phone)
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

        return Response({"detail": "OTP is valid"}, status=status.HTTP_200_OK)


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
            user = CustomUser.objects.get(email=email) if method == 'email' else CustomUser.objects.get(phone=phone)
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

        user.set_password(new_password)
        user.save()

        otp_record.used = True
        otp_record.save()

        return Response({"detail": "Password has been reset successfully"}, status=status.HTTP_200_OK)


