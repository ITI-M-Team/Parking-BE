import qrcode
import json
from io import BytesIO
from django.core.files.base import ContentFile

def generate_qr_code_for_booking(booking):
    # 💡 البيانات اللي هتتحط جوا الـ QR
    data = {
        "id": booking.id,
        "garage_name": booking.garage.name,
        "spot_id": booking.parking_spot.id,
        "estimated_arrival_time": booking.estimated_arrival_time.isoformat(),
        "reservation_expiry_time": booking.reservation_expiry_time.isoformat(),
        "estimated_cost": float(booking.estimated_cost),
        "status": booking.status,
    }

    # 🧠 نحولها لـ JSON String عشان نحطها في الـ QR
    qr_data = json.dumps(data, indent=2)

    # 🧾 توليد الـ QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # 🖼️ حفظ الصورة في الميموري كـ file
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    file_content = ContentFile(buffer.getvalue())

    # 📝 حفظ الصورة في حقل الـ Booking
    filename = f"booking_{booking.id}.png"
    booking.qr_code_image.save(filename, file_content)
    booking.save()

    return booking.qr_code_image.url
