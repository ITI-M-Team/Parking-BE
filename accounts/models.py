from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

# Create your models here.
class CustomUser(AbstractUser):
    ROLE_CHOICES=(
        ('driver', 'Driver'),
        ('garage_owner', 'Garage Owner'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    verification_status= models.CharField(
        max_length=20,
        default='Pending',
        choices=(
            ('Pending', 'Pending'),
            ('Verified', 'Verified'),
            ('Rejected', 'Rejected'),
        )
    )
    national_id = models.CharField(
        max_length=14,
        unique=True,
        blank=False,
        null=False,
        

        )
    driver_license = models.FileField(upload_to='documents/driver/', blank=True, null=True)
    car_license = models.FileField(upload_to='documents/car/' , blank=True, null=True)
    national_id_img = models.FileField(upload_to='documents/national_id/', blank=True, null=True) 

    def __str__(self):
        return self.username
    
    def clean(self):
        #validate national ID
        if len(self.national_id) != 14:
            raise ValidationError("National ID Must be 14 digits: ")
        
        super().clean()