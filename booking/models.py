from django.db import models
from django.utils import timezone
from datetime import timedelta
from accounts.models import CustomUser
from garage.models import ParkingSpot, Garage
from django.core.validators import FileExtensionValidator

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('confirmed_late',   'Confirmed Late'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('awaiting_payment',   'Awaiting Payment'), 
        ('blocked','Blocked'),
    ]

    driver = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    garage = models.ForeignKey(Garage, on_delete=models.CASCADE)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    parking_spot = models.ForeignKey(ParkingSpot, on_delete=models.CASCADE)
    estimated_arrival_time = models.DateTimeField(null=True, blank=True)
    estimated_cost = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    reservation_expiry_time = models.DateTimeField()
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    # 💡 أضف الحقل التالى بعد estimated_cost مباشرة
    actual_cost = models.DecimalField(
        max_digits=8,          # رقم أكبر قليلًا تحسّبًا
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
        help_text="التكلفة الفعلية (مدة الانتظار + مدة الركن)"
    )

    qr_code_image = models.ImageField(
        upload_to='qr_codes/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['png'])]
    )
    late_alert_sent = models.BooleanField(default=False)
    confirmation_time = models.DateTimeField(            # ⬅️ new
        null=True, blank=True,
        help_text="Timestamp when driver confirmed after expiry"
    )
    confirmed_late_at = models.DateTimeField(null=True, blank=True)
    waiting_time = models.DurationField(null=True, blank=True)
    


    def save(self, *args, **kwargs):
        if not self.reservation_expiry_time and self.estimated_arrival_time:
            # Automatically set expiry time based on arrival + grace period
            self.reservation_expiry_time = self.estimated_arrival_time + timedelta(
                minutes=self.garage.reservation_grace_period
            )
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.reservation_expiry_time


    def __str__(self):
        return f"Booking {self.id} by {self.driver.email}"
    
    def total_parking_time(self):
        """
        Returns a timedelta covering BOTH:
         Handles late confirmations via confirmed_late_at.
    """
        if self.end_time:
            start_reference = self.confirmed_late_at or self.confirmation_time
            if start_reference:
                return self.end_time - start_reference
        return None
    @property
    def calculated_waiting_time(self):
        """
        الزمن من لحظة تأكيد الحجز المتأخر → لحظة الدخول (scan QR)
        """
        if self.confirmation_time and self.start_time:
            return self.start_time - self.confirmation_time
        return None

    @property
    def garage_time(self):
        """
        الزمن الفعلي داخل الجراج (من الدخول حتى الخروج)
        """
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
       # ───────── تمثيل نصى ─────────
    def __str__(self):
        return f"Booking {self.id} — {self.driver.email}"

    class Meta:
        ordering = ["-created_at"]