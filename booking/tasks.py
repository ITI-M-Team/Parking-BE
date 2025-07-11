from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from .models import Booking
from garage.models import ParkingSpot


@shared_task
def notify_before_expiry(booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)

        if booking.status == "pending":
            user = booking.driver
            garage_name = booking.garage.name
            expiry_time = booking.reservation_expiry_time.strftime('%Y-%m-%d %H:%M')

            subject = "⚠️ Reminder: Your Reservation Will Expire in 5 Minutes"
            message = (
                f"Hi {user.first_name},\n\n"
                f"Just a reminder: your reservation at '{garage_name}' will expire at {expiry_time}.\n"
                f"Please make sure to arrive before that time.\n\n"
                f"Thank you,\nParking System"
            )

            send_mail(
                subject=subject,
                message=message,
                from_email="Parking System <appparking653@gmail.com>",
                recipient_list=[user.email],
                fail_silently=False,
            )

            print("🔔 [Reminder] 5 minutes before expiry sent.")

    except Booking.DoesNotExist:
        print(f"❌ Booking with ID {booking_id} not found.")


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

            # Notify user by email
            user = booking.driver
            subject = "❌ Your Reservation Has Expired"
            message = (
                f"Hi {user.first_name},\n\n"
                f"Your reservation at '{booking.garage.name}' has expired.\n"
                f"The reserved parking spot has been released.\n\n"
                f"Thank you,\nParking System"
            )

            send_mail(
                subject=subject,
                message=message,
                from_email="Parking System <appparking653@gmail.com>",
                recipient_list=[user.email],
                fail_silently=False,
            )

            print("⛔️ [Expired] Email sent and spot released.")

    except Booking.DoesNotExist:
        print(f"❌ Booking with ID {booking_id} not found.")
