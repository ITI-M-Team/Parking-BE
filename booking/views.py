from datetime import timedelta
import logging

from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from booking.models import Booking
from booking.serializers import BookingInitiationSerializer, BookingDetailSerializer
from booking.tasks import expire_or_block_booking, notify_before_expiry
from booking.utils import generate_qr_code_for_booking, send_booking_confirmation_email
from garage.models import ParkingSpot

logger = logging.getLogger(__name__)
User = get_user_model()
class BookingInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BookingInitiationSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        garage = serializer.validated_data["garage"]
        spot = serializer.validated_data["spot"]
        estimated_fee = serializer.validated_data["estimated_cost"]
        grace = serializer.validated_data["grace_period"]
        user = request.user

        # Check if garage is open now
        now = timezone.localtime().time()
        opening = garage.opening_hour
        closing = garage.closing_hour

        if opening < closing:
            # Normal case: open and close on the same day
            if not (opening <= now <= closing):
                return Response({
                    "error": f"الجراج مغلق حاليًا. ساعات العمل من {opening.strftime('%H:%M')} إلى {closing.strftime('%H:%M')}."
                }, status=400)
        else:
            # Overnight case: e.g. opening at 20:00, closing at 06:00 next day
            if not (now >= opening or now <= closing):
                return Response({
                    "error": f"الجراج مغلق حاليًا. ساعات العمل من {opening.strftime('%H:%M')} إلى {closing.strftime('%H:%M')}."
                }, status=400)

        # Blocked user
        if user.blocked_until and user.blocked_until > timezone.now():
            return Response({"error": f"لا يمكنك الحجز قبل {user.blocked_until}"}, status=403)

        # Check if user already has any active booking
        if Booking.objects.filter(
            driver=user,
            status__in=["pending", "confirmed", "confirmed_late", "awaiting_response"],
            reservation_expiry_time__gt=timezone.now(),
        ).exists():
            return Response({"error": "لديك حجز قائم بالفعل."}, status=400)

        # Check if the user already booked this spot
        if Booking.objects.filter(
            driver=user,
            parking_spot=spot,
            status__in=["pending", "confirmed", "confirmed_late", "awaiting_response"],
            reservation_expiry_time__gt=timezone.now(),
        ).exists():
            return Response({"error": "لقد قمت بالفعل بحجز هذا المكان مسبقًا."}, status=400)

        # Check wallet balance
        if user.wallet_balance < estimated_fee:
            return Response({"error": "رصيد المحفظة غير كافٍ."}, status=400)

        # Reserve the spot
        spot.status = "reserved"
        spot.save()

        # Deduct wallet
        user.wallet_balance -= estimated_fee
        user.save(update_fields=["wallet_balance"])

        # Create booking
        now = timezone.now()
        expiry = now + timedelta(minutes=grace)

        booking = Booking.objects.create(
            driver=user,
            garage=garage,
            parking_spot=spot,
            estimated_cost=estimated_fee,
            reservation_expiry_time=expiry,
            status="pending",
        )

        # Generate QR and send email
        generate_qr_code_for_booking(booking)
        send_booking_confirmation_email(booking)

        # Schedule background tasks
        notify_before_expiry.apply_async((booking.id,), eta=booking.reservation_expiry_time)
        expire_or_block_booking.apply_async(
            (booking.id,), eta=booking.reservation_expiry_time + timedelta(minutes=1)
        )

        return Response({
            "booking_id": booking.id,
            "estimated_cost": float(estimated_fee),
            "reservation_expiry_time": booking.reservation_expiry_time.isoformat(),
            "qr_code_url": booking.qr_code_image.url if booking.qr_code_image else None,
            "wallet_balance": float(user.wallet_balance),
        }, status=201)

class BookingDetailView(RetrieveAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingDetailSerializer
    lookup_field = "id"
    lookup_url_kwarg = "id"


class ActiveBookingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        booking = Booking.objects.filter(driver=request.user).exclude(
            status__in=["cancelled", "expired", "completed"]
        ).order_by("-created_at").first()

        if booking:
            return Response(BookingDetailSerializer(booking).data)

        recent = Booking.objects.filter(
            driver=request.user, status="completed", end_time__gte=now - timedelta(seconds=30)
        ).order_by("-end_time").first()

        if recent:
            data = BookingDetailSerializer(recent).data
            data["exit_summary"] = True
            return Response(data)

        return Response({"detail": "No active bookings."}, status=404)


class CancelBookingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id, driver=request.user)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found."}, status=404)

        if booking.status != "pending":
            return Response({"error": "Can cancel only pending bookings."}, status=400)

        if timezone.now() > booking.reservation_expiry_time:
            return Response({"error": "Grace‑period ended."}, status=400)

        booking.status = "cancelled"
        booking.save(update_fields=["status"])

        spot = booking.parking_spot
        spot.status = "available"
        spot.save(update_fields=["status"])

        return Response({"success": "Booking cancelled."})


class BookingLateDecisionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            booking = Booking.objects.get(id=id, driver=request.user)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found."}, status=404)

        if booking.status != "awaiting_response":
            return Response({"error": "Action not allowed in current booking state."}, status=400)

        action = request.data.get("action")
        now = timezone.now()

        if action == "confirm":
            booking.status = "confirmed_late"
            booking.confirmed_late_at = now
            booking.confirmation_time = now
            booking.reservation_expiry_time = now
            booking.late_alert_sent = True
            booking.save(update_fields=[
                "status", "confirmed_late_at", "reservation_expiry_time", "late_alert_sent", "confirmation_time"
            ])

            logger.info(
                f"User {request.user.id} CONFIRMED late booking {booking.id} at {now.isoformat()}"
            )

            return Response({
                "success": "Booking confirmed (late confirmation).",
                "confirmation_time": booking.confirmation_time.isoformat()
            })

        elif action == "cancel":
            expire_or_block_booking.apply_async((booking.id,), countdown=1)

            logger.info(
                f"User {request.user.id} CANCELLED late booking {booking.id} at {now.isoformat()}"
            )

            return Response({
                "success": "Booking cancellation in progress."
            })

        return Response({
            "error": "Invalid action. Must be either 'confirm' or 'cancel'."
        }, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def scan_qr_code(request):
    booking_id = request.data.get("booking_id")
    try:
        booking = Booking.objects.select_related("parking_spot", "garage").get(id=booking_id, driver=request.user)
    except Booking.DoesNotExist:
        return Response({"error": "Invalid QR."}, status=404)

    now = timezone.now()

    if booking.status in ("pending", "confirmed_late"):
        if booking.start_time is None:
            booking.status = "confirmed"
            booking.start_time = now
            if not booking.confirmation_time:
                booking.confirmation_time = now
            if booking.confirmed_late_at:
                booking.waiting_time = now - booking.confirmed_late_at
            else:
                booking.waiting_time = now - booking.created_at

            booking.save(update_fields=["status", "start_time", "waiting_time", "confirmation_time"])

        return Response({
            "message": "Entry recorded",
            "action": "entry",
            "start_time": booking.start_time,
            "stop_timer": True
        })

    if booking.status == "confirmed":
        booking.status = "completed"
        booking.end_time = now

        duration = booking.total_parking_time()
        hours = duration.total_seconds() / 3600
        booking.actual_cost = hours * float(booking.garage.price_per_hour)
        booking.save(update_fields=["status", "end_time", "actual_cost"])

        spot = booking.parking_spot
        spot.status = "available"
        spot.save(update_fields=["status"])

        return Response({
            "message": "Exit recorded",
            "action": "exit",
            "start_time": booking.start_time,
            "end_time": booking.end_time,
            "waiting_time_minutes": int(booking.waiting_time.total_seconds() / 60) if booking.waiting_time else 0,
            "garage_time_minutes": int(booking.garage_time.total_seconds() / 60) if booking.garage_time else 0,
            "total_duration_minutes": int(duration.total_seconds() / 60),
            "actual_cost": round(booking.actual_cost, 2),
            "exit_summary": True,
        })

    return Response({"error": "Invalid QR state."}, status=400)
