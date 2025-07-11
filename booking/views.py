from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveAPIView
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import logging

from .models import Booking
from garage.models import ParkingSpot
from .serializers import BookingInitiationSerializer, BookingDetailSerializer
from .tasks import send_expiry_warning, notify_before_expiry
from .utils import generate_qr_code_for_booking, send_booking_confirmation_email

logger = logging.getLogger(__name__)
User = get_user_model()


class BookingInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = BookingInitiationSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                garage = serializer.validated_data['garage']
                spot = serializer.validated_data['spot']
                arrival_time = serializer.validated_data['estimated_arrival_time']
                estimated_cost = serializer.validated_data['estimated_cost']
                grace_period = serializer.validated_data['grace_period']

                user = request.user

                # Check for existing conflicting bookings
                existing_booking = Booking.objects.filter(
                    driver=user,
                    status__in=["pending", "active"],
                    reservation_expiry_time__gt=timezone.now()
                ).first()

                if existing_booking:
                    return Response(
                        {"error": "Booking failed. You already have a conflicting booking."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Check for wallet balance
                if user.wallet_balance < estimated_cost:
                    return Response(
                        {"error": "Insufficient wallet balance"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Reserve the spot
                spot.status = 'reserved'
                spot.save()

                # Deduct amount from wallet
                user.wallet_balance -= estimated_cost
                user.save()

                # Calculate expiry time
                expiry_time = arrival_time + timedelta(minutes=grace_period)

                # Create booking
                booking = Booking.objects.create(
                    driver=user,
                    garage=garage,
                    parking_spot=spot,
                    estimated_arrival_time=arrival_time,
                    estimated_cost=estimated_cost,
                    reservation_expiry_time=expiry_time,
                    status='pending'
                )

                # Generate QR code
                generate_qr_code_for_booking(booking)

                # ✅ Send confirmation email
                send_booking_confirmation_email(booking)

                # Schedule expiry notifications
                send_expiry_warning.apply_async((booking.id,), countdown=grace_period * 60)
                if grace_period > 5:
                    notify_before_expiry.apply_async((booking.id,), countdown=(grace_period - 5) * 60)

                # Return response
                return Response({
                    "booking_id": booking.id,
                    "estimated_cost": float(estimated_cost),
                    "reservation_expiry_time": booking.reservation_expiry_time.isoformat(),
                    "qr_code_url": booking.qr_code_image.url if booking.qr_code_image else None,
                    "wallet_balance": float(user.wallet_balance),
                    "status": "success"
                }, status=status.HTTP_201_CREATED)

            logger.warning("❌ Serializer Errors: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("🚨 Full booking exception:")
            return Response(
                {"error": "🚨 Error during booking. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BookingDetailView(RetrieveAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingDetailSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
