from celery import shared_task
from django.utils import timezone
from booking.models import Booking

def block_user(user):
    # Block user for 24 hours (customize as needed)
    user.blocked_until = timezone.now() + timezone.timedelta(minutes=24)
    user.save(update_fields=["blocked_until"])

@shared_task
def handle_late_confirmation_no_entry(booking_id):
    try:
        booking = Booking.objects.select_related("driver", "garage").get(id=booking_id)
    except Booking.DoesNotExist:
        return

    if booking.status == "confirmed_late" and booking.start_time is None:
        driver = booking.driver
        price_per_hour = booking.garage.price_per_hour
        user_email = driver.email
        garage_name = booking.garage.name

        from django.core.mail import send_mail

        if driver.wallet_balance >= price_per_hour:
            driver.wallet_balance -= price_per_hour
            driver.save(update_fields=["wallet_balance"])
            booking.status = "cancelled"
            booking.save(update_fields=["status"])

            # Send email: cancelled and charged
            subject = "Booking Cancelled – One Hour Charge Deducted"
            body = (
                f"Hello {driver.first_name},\n\n"
                f"Your booking at {garage_name} has been cancelled because you did not enter within one hour of late confirmation.\n"
                f"We have deducted the hourly fee of {price_per_hour} EGP from your wallet.\n\n"
                f"Thank you,\n"
                f"Parking System"
            )
            send_mail(subject, body, "Parking System <noreply@parking.com>", [user_email], fail_silently=True)
        else:
            booking.status = "cancelled"
            booking.save(update_fields=["status"])
            block_user(driver)

            # Send email: cancelled and blocked
            subject = "Booking Cancelled – You’ve Been Temporarily Blocked"
            body = (
                f"Hello {driver.first_name},\n\n"
                f"Your booking at {garage_name} has been cancelled because you did not enter within one hour of late confirmation.\n"
                f"You didn’t have enough balance in your wallet, so we’ve temporarily blocked your account from making new bookings for 24 hours.\n\n"
                f"Thank you,\n"
                f"Parking System"
            )
            send_mail(subject, body, "Parking System <noreply@parking.com>", [user_email], fail_silently=True)
