from django.db import models
from django.core.exceptions import ValidationError

class Garage(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    opening_hour = models.TimeField()
    closing_hour = models.TimeField()
    image = models.ImageField(upload_to='garage_images/', null=True, blank=True)
    price_per_hour = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    reservation_grace_period = models.PositiveIntegerField(
        default=15,
        help_text="مدة الحجز المؤقت بالدقائق قبل إلغائه تلقائيًا"
    )


    def clean(self):
        if not (22 <= self.latitude <= 32):
            raise ValidationError({'latitude': 'Latitude must be between 22 and 32 (Egypt only).'})
        if not (25 <= self.longitude <= 35):
            raise ValidationError({'longitude': 'Longitude must be between 25 and 35 (Egypt only).'})
        if self.price_per_hour < 0:
            raise ValidationError({'price_per_hour': 'Hourly rate must be positive or zero.'})
        
       
    def __str__(self):
        return self.name

class GarageReview(models.Model):
    garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField()

class ParkingSpot(models.Model):
    STATUS_CHOICES = [
    ('available', 'Available'),
    ('occupied', 'Occupied'),
    ('reserved', 'Reserved'),
]
    garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='spots')
    slot_number = models.CharField(max_length=10)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='available')
