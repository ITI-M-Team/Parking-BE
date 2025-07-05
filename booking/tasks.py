from celery import shared_task
from django.utils import timezone
from .models import Booking
from garage.models import ParkingSpot

@shared_task
def send_expiry_warning(booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)

        if booking.status == "pending" and timezone.now() > booking.reservation_expiry_time:
            booking.status = "awaiting_response"
            booking.save()

            spot = booking.parking_spot
            spot.status = "available"
            spot.save()

            print("🚨 التنبيه: لم يصل السائق في الوقت المحدد.")

    except Booking.DoesNotExist:
        print(f"❌ Booking {booking_id} not found.")
