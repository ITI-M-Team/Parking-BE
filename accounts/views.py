
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.mail import send_mail
from django.conf import settings
from .models import CustomUser
from rest_framework.views import APIView
from .serializers import RegisterSerializer , CustomTokenObtainPairSerializer

from .serializers import RegisterSerializer, CustomTokenObtainPairSerializer

from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str




class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def perform_create(self, serializer):
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
class ActivateUserView(APIView):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)

            if user.is_active:
                return Response({'message': 'Account already activated.'})

            if default_token_generator.check_token(user, token):
                user.is_active = True
                user.save()
                return Response({'message': 'Account activated successfully.'}, status=200)
            else:
                return Response({'error': 'Invalid activation token.'}, status=400)

        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response({'error': 'Invalid activation link.'}, status=400)        


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer



# ##GEt user info 
class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "national_id": user.national_id,
            "phone": user.phone,
            "driver_license": user.driver_license.url if user.driver_license else None,
            "car_license": user.car_license.url if user.car_license else None,
            "national_id_img": user.national_id_img.url if user.national_id_img else None,
        })


