from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Avg
from accounts.models import CustomUser 
class Garage(models.Model):
    ##############Mandatory to know garage owner ###################
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='owned_garages', limit_choices_to={'role': 'garage_owner'})
    ###############################################
    name = models.CharField(max_length=100)
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    opening_hour = models.TimeField()
    closing_hour = models.TimeField()
    image = models.ImageField(upload_to='garage_images/', null=True, blank=True)
    # Contract document field (required)
    contract_document = models.FileField(
        upload_to='garage_contracts/', 
        null=False, 
        blank=False,
        help_text="Upload garage contract document (PDF, DOC, DOCX) or image (JPG, PNG, JPEG)"
    )
      # Add verification status field
    verification_status = models.CharField(
        max_length=20,
        default='Pending',
        choices=(
            ('Pending', 'Pending'),
            ('Verified', 'Verified'),
            ('Rejected', 'Rejected'),
        )
    )

    
    price_per_hour = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    reservation_grace_period = models.PositiveIntegerField(
        default=15,
        help_text="مدة الحجز المؤقت بالدقائق قبل إلغائه تلقائيًا"
    )

    #   جديد: عدد الساعات التي يُحظر فيها السائق لو ألغى بعد انتهاء المهلة
    block_duration_hours = models.PositiveIntegerField(
        default=3,
        help_text="عدد ساعات الحظر عند الإلغاء المتأخر"
    )



    def clean(self):
        if not (22 <= self.latitude <= 32):
            raise ValidationError({'latitude': 'Latitude must be between 22 and 32 (Egypt only).'})
        if not (25 <= self.longitude <= 35):
            raise ValidationError({'longitude': 'Longitude must be between 25 and 35 (Egypt only).'})
        if self.price_per_hour < 0:
            raise ValidationError({'price_per_hour': 'Hourly rate must be positive or zero.'})
        
        #Validate contract document file type
        if self.contract_document:
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
            file_extension = self.contract_document.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise ValidationError({
                    'contract_document': 'Only PDF, DOC, DOCX, JPG, JPEG, and PNG files are allowed for contract documents.'
                })
    
   
    def __str__(self):
        return self.name
# New model for garage verification requests
class GarageVerificationRequest(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Verified', 'Verified'),
        ('Rejected', 'Rejected'),
    )
    
    garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='verification_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    reason = models.TextField(blank=True, null=True, help_text="Reason for rejection or additional notes")
    reviewed_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_garage_requests',
        limit_choices_to={'is_superuser': True}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Garage Verification Request"
        verbose_name_plural = "Garage Verification Requests"
    
    def __str__(self):
        return f"Garage Verification Request for {self.garage.name} - {self.status}"
class GarageReview(models.Model):
    driver = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField()  # 1 to 5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    booking = models.OneToOneField('booking.Booking', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = ('driver', 'booking')  # one review per driver per garage

    def __str__(self):
        return f"{self.driver} - {self.rating}"

class ParkingSpot(models.Model):
    STATUS_CHOICES = [
    ('available', 'Available'),
    ('occupied', 'Occupied'),
    ('reserved', 'Reserved'),
]
    garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='spots')
    slot_number = models.CharField(max_length=10)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='available')
    def __str__(self):
        return f"{self.garage.name} - Spot {self.slot_number}"
