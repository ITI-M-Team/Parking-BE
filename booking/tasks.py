from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail

from booking.models import Booking


@shared_task
def notify_before_expiry(booking_id: int) -> None:
    try:
        booking = (
            Booking.objects
            .select_related("driver", "garage")
            .get(id=booking_id)
        )

        # If already confirmed_late, don't send notification
        if (
            booking.status == "pending"
            and not booking.late_alert_sent
            and booking.confirmed_late_at is None
            and timezone.now() >= booking.reservation_expiry_time
        ):
            user = booking.driver
            garage_name = booking.garage.name

            subject = "⏰ Booking Time Expired – Action Required"
            body = (
                f"Hello {user.first_name},\n\n"
                f"Your reservation time at **{garage_name}** has expired.\n"
                f"You can now:\n"
                f"• Click (Confirm) to proceed with the booking and pay, or\n"
                f"• Click (Cancel), which will result in a temporary block.\n\n"
                f"Thank you,\n"
                f"Parking System"
            )

            send_mail(
                subject,
                body,
                "Parking System <noreply@parking.com>",
                [user.email],
                fail_silently=True,
            )

            booking.late_alert_sent = True
            booking.status = "awaiting_response"
            booking.save(update_fields=["late_alert_sent", "status"])

            print(
                f"[notify_before_expiry] booking {booking_id} → awaiting_response; mail sent to {user.email}"
            )

    except Booking.DoesNotExist:
        print(f"[notify_before_expiry] booking {booking_id} not found")


@shared_task
def expire_or_block_booking(booking_id: int) -> None:
    try:
        booking = (
            Booking.objects
            .select_related("parking_spot", "driver", "garage")
            .get(id=booking_id)
        )
        now = timezone.now()

        if booking.status in ("confirmed", "confirmed_late", "completed", "awaiting_payment"):
            return

        if now < booking.reservation_expiry_time:
            return

        booking.status = "expired"
        booking.save(update_fields=["status"])

        spot = booking.parking_spot
        spot.status = "available"
        spot.save(update_fields=["status"])

        driver = booking.driver
        block_hours = getattr(booking.garage, "block_duration_hours", 3) or 1
        driver.blocked_until = now + timedelta(hours=block_hours)
        driver.save(update_fields=["blocked_until"])

        subject = "Booking Cancelled – Temporary Block Applied"
        body = (
            f"Hello {driver.first_name},\n\n"
            f"Your booking at {booking.garage.name} has been cancelled due to no confirmation.\n"
            f"You have been temporarily blocked from creating new bookings for {block_hours} hour(s).\n\n"
            f"Thank you,\n"
            f"Parking System"
        )
        send_mail(
            subject,
            body,
            "Parking System <noreply@parking.com>",
            [driver.email],
            fail_silently=True,
        )

        print(
            f"[expire_or_block_booking] booking {booking_id} expired, spot {spot.id} freed, user {driver.email} blocked for {block_hours} h"
        )

    except Booking.DoesNotExist:
        print(f"[expire_or_block_booking] booking {booking_id} not found")
