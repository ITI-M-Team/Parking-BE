from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('driver', 'Driver'),
        ('garage_owner', 'Garage Owner'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    verification_status = models.CharField(
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
        verbose_name="National ID"
    )
    phone = models.CharField(
        max_length=15,
        unique=True,
        blank=False,
        null=False,
        verbose_name="Phone Number"
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        blank=False,
        null=False,
        verbose_name="Username"
    )
    email = models.EmailField(_('email address'), unique=True)
    driver_license = models.FileField(upload_to='documents/driver/', blank=True, null=True)
    car_license = models.FileField(upload_to='documents/car/', blank=True, null=True)
    national_id_img = models.FileField(upload_to='documents/national_id/', blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'phone', 'national_id']

    def __str__(self):
        return self.email

    def clean(self):
        if len(self.national_id) != 14:
            raise ValidationError(_("National ID must be exactly 14 digits"))
        
        egyptian_phone_prefixes = ('010', '011', '012', '015')
        if not self.phone.startswith(egyptian_phone_prefixes):
            raise ValidationError(_("Phone number must be an Egyptian number starting with 010, 011, etc."))

        if len(self.phone) != 11:
            raise ValidationError(_("Phone number must be 11 digits"))

        super().clean()


class Garage(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    hourly_rate = models.DecimalField(max_digits=6, decimal_places=2)
    available_spots = models.IntegerField()
    average_rating = models.FloatField(default=0.0)

    def __str__(self):
        return self.name
