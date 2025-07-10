from celery import shared_task
from django.utils import timezone
from .models import Booking
from garage.models import ParkingSpot

@shared_task
def send_expiry_warning(booking_id):
    try:
        booking = Booking.objects.select_related("parking_spot").get(id=booking_id)

        if booking.status == "pending" and timezone.now() > booking.reservation_expiry_time:
            # Expire booking
            booking.status = "expired"
            booking.save(update_fields=["status"])

            # Free the parking spot
            spot = booking.parking_spot
            spot.status = "available"
            spot.save(update_fields=["status"])

            print(f"🚨 Spot {spot.id} is now available (booking {booking.id} expired).")

    except Booking.DoesNotExist:
        print(f"❌ Booking {booking_id} not found.")
