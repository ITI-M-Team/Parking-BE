from django.db import models
from django.utils import timezone
from accounts.models import CustomUser
from garage.models import ParkingSpot, Garage
from django.core.validators import FileExtensionValidator

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    driver = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    garage = models.ForeignKey(Garage, on_delete=models.CASCADE)
    parking_spot = models.ForeignKey(ParkingSpot, on_delete=models.CASCADE)
    estimated_arrival_time = models.DateTimeField()
    estimated_cost = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    reservation_expiry_time = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    qr_code_image = models.ImageField(
        upload_to='qr_codes/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['png'])]
    )

    def is_expired(self):
        return timezone.now() > self.reservation_expiry_time

    def __str__(self):
        return f"Booking {self.id} by {self.driver.email}"
