import qrcode
import json
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings  # ✅ لازم تضيف ده فوق


def generate_qr_code_for_booking(booking):
    data = {
        "id": booking.id,
        "garage_name": booking.garage.name,
        "spot_id": booking.parking_spot.id,
        "estimated_arrival_time": booking.estimated_arrival_time.isoformat(),
        "reservation_expiry_time": booking.reservation_expiry_time.isoformat(),
        "estimated_cost": float(booking.estimated_cost),
        "status": booking.status,
    }

    qr_data = json.dumps(data, indent=2)

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    file_content = ContentFile(buffer.getvalue())

    filename = f"booking_{booking.id}.png"
    booking.qr_code_image.save(filename, file_content)
    booking.save()

    return booking.qr_code_image.url


def send_booking_confirmation_email(booking):
    subject = f"Booking Confirmation - Booking #{booking.id}"
    
    context = {
        "booking": booking,
        "qr_code_url": booking.qr_code_image.url,
    }

    body = render_to_string("emails/booking_confirmation.html", context)

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=f"Parking System <{settings.EMAIL_HOST_USER}>",  # ✅ ده التعديل الأساسي
        to=[booking.driver.email],
        reply_to=[booking.driver.email],
    )
    email.content_subtype = "html"  

    if booking.qr_code_image:
        email.attach_file(booking.qr_code_image.path)

    email.send()
