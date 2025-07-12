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
from rest_framework.decorators import api_view, permission_classes

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

                # Send confirmation email
                send_booking_confirmation_email(booking)

                # Schedule expiry notifications
                send_expiry_warning.apply_async((booking.id,), countdown=grace_period * 60)
                if grace_period > 5:
                    notify_before_expiry.apply_async((booking.id,), countdown=(grace_period - 5) * 60)

                return Response({
                    "booking_id": booking.id,
                    "estimated_cost": float(estimated_cost),
                    "reservation_expiry_time": booking.reservation_expiry_time.isoformat(),
                    "qr_code_url": booking.qr_code_image.url if booking.qr_code_image else None,
                    "wallet_balance": float(user.wallet_balance),
                    "status": "success"
                }, status=status.HTTP_201_CREATED)

            logger.warning("Serializer errors: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception("Error during booking:")
            return Response(
                {"error": "Error during booking. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BookingDetailView(RetrieveAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingDetailSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id'



# =====================================================

class CancelBookingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id, driver=request.user)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found."}, status=404)

        if booking.status != 'pending':
            return Response({"error": "Only pending bookings can be cancelled."}, status=400)

        if timezone.now() > booking.reservation_expiry_time:
            return Response({"error": "Cannot cancel booking after grace period ends."}, status=400)

        booking.status = 'cancelled'
        booking.save()

        spot = booking.parking_spot
        spot.status = 'available'
        spot.save()

        return Response({"success": "Booking cancelled and spot is now available."}, status=200)


class ActiveBookingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()

        active_booking = Booking.objects.filter(
            driver=request.user
        ).exclude(status__in=['cancelled', 'expired']).order_by('-created_at').first()



        if active_booking:
            serializer = BookingDetailSerializer(active_booking)
            return Response(serializer.data, status=200)

       
        recent_completed = Booking.objects.filter(
            driver=request.user,
            status='completed',
            end_time__gte=now - timedelta(seconds=30)  
        ).order_by('-end_time').first()

        if recent_completed:
            serializer = BookingDetailSerializer(recent_completed)
            return Response({"exit_summary": True, **serializer.data}, status=200)

        return Response({"detail": "No active bookings found."}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def scan_qr_code(request):
    booking_id = request.data.get("booking_id")

    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found."}, status=404)

    if booking.status == 'pending':
        booking.status = 'confirmed'
        booking.start_time = timezone.now()
        booking.save()
        return Response({
            "message": "Entry recorded", 
            "start_time": booking.start_time,
            "action": "entry"
        }, status=200)

    elif booking.status == 'confirmed':
        booking.status = 'completed'
        booking.end_time = timezone.now()
        
        total_duration = booking.end_time - booking.start_time
        total_hours = total_duration.total_seconds() / 3600
        
        actual_cost = total_hours * float(booking.garage.price_per_hour)
        booking.actual_cost = actual_cost
        
        booking.save()
        
        spot = booking.parking_spot
        spot.status = 'available'
        spot.save()
        
        return Response({
            "message": "Exit recorded",
            "action": "exit",
            "start_time": booking.start_time,
            "end_time": booking.end_time,
            "total_duration_minutes": int(total_duration.total_seconds() / 60),
            "total_hours": round(total_hours, 2),
            "actual_cost": round(actual_cost, 2),
            "garage_name": booking.garage.name,
            "spot_id": booking.parking_spot.slot_number,
            "exit_summary": True
        }, status=200)

    return Response({"error": "Invalid booking state for scanning."}, status=400)
# =====================================================