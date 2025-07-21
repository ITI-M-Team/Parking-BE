from rest_framework import generics, permissions , status
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.conf import settings
from django.db.models import Q

from .models import *
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
            "verification_status":user.verification_status,
            "is_superuser": user.is_superuser,
            "wallet_balance": float(user.wallet_balance),
            "driver_license": build_url(user.driver_license),
            "car_license": build_url(user.car_license),
            "national_id_img": build_url(user.national_id_img),
            "profile_image": build_url(user.profile_image),
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

### List all user's requests to be reviewed ####
class VerificationRequestListView(generics.ListAPIView):
    serializer_class = VerificationRequestSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        queryset = VerificationRequest.objects.all().order_by('-created_at')
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset
    
###   -------Send email notification to user about verification status _______
def send_verification_email(user, verification_status, reason='', is_resubmission=False):
    subject_map = {
        'Verified': 'Account Verified - Welcome!',
        'Rejected': 'Account Verification Rejected',
        'Pending': 'Account Under Review'
    }
    if is_resubmission and verification_status == 'Pending':
        subject = 'Document Resubmission Received - Under Review'
    else:
        subject = subject_map.get(verification_status, 'Account Status Update')
    context = {
        'user': user,
        'status': verification_status,
        'reason': reason,
        'is_resubmission': is_resubmission,
        'site_name': getattr(settings, 'Smart Parking', 'Smart Parking'),
    }
    html_message = render_to_string('emails/verification_status.html', context)
    plain_message = strip_tags(html_message)
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )

#########   Update verification status and send email notification    ###########

@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def update_verification_status(request, request_id):
    verification_request = get_object_or_404(VerificationRequest, id=request_id)
    serializer = VerificationActionSerializer(data=request.data)
    
    if serializer.is_valid():
        new_status = serializer.validated_data['status']
        reason = serializer.validated_data.get('reason', '')
        
        old_status = verification_request.status
        # ___Update verification request__
        verification_request.status = new_status
        verification_request.reason = reason
        verification_request.reviewed_by = request.user
        verification_request.save()
        
        # +____Update user verification status___
        user = verification_request.user
        user.verification_status = new_status
        user.save()
        # ### Send email notification---------
        send_verification_email(user, new_status, reason)
        return Response({
            'message': 'Verification status updated successfully',
            'status': new_status,
            'user_email': user.email,
            'previous_status': old_status
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

##### ----------   Get verification statistics for dashboard   -------------- ######

@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def verification_stats(request):
    total_requests = VerificationRequest.objects.count()
    pending_requests = VerificationRequest.objects.filter(status='Pending').count()
    verified_requests = VerificationRequest.objects.filter(status='Verified').count()
    rejected_requests = VerificationRequest.objects.filter(status='Rejected').count()

    # Had a reason before (was rejected)##
    resubmission_count = VerificationRequest.objects.filter(
        status='Pending',
        reason__isnull=False  
    ).count()

    return Response({
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'verified_requests': verified_requests,
        'rejected_requests': rejected_requests,
        'resubmission_count': resubmission_count,
        'verification_rate': (verified_requests / total_requests * 100) if total_requests > 0 else 0
    })