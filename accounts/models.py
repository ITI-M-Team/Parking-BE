import os
from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from twilio.rest import Client


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
        verbose_name="Username",
    )
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)


    
    email = models.EmailField(_('email address'), unique=True)
    driver_license = models.FileField(upload_to='documents/driver/', blank=True, null=True)
    car_license = models.FileField(upload_to='documents/car/', blank=True, null=True)
    national_id_img = models.FileField(upload_to='documents/national_id/', blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/',blank=True,null=True,verbose_name="Profile Image")
    blocked_until = models.DateTimeField(null=True, blank=True)




    # Add a field to track wallet balance
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    EMAIL_FIELD = 'email'
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
# Profile Image Validation
        if self.profile_image:
            ###add limit for image maximum  5MB limit
            if self.profile_image.size > 5 * 1024 * 1024:  
                raise ValidationError(_("Profile image must be less than 5MB"))
        
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        ext = os.path.splitext(self.profile_image.name)[1].lower()
        if ext not in valid_extensions:
            raise ValidationError(_("Profile image must be a valid image file (jpg, jpeg, png, gif)"))
        super().clean()
    ### """Check if user has uploaded any documents"""
    @property
    def has_documents(self):
        return bool(self.driver_license or self.car_license or self.national_id_img)
    
    ###"""Get list of missing documents based on role"""
    @property
    def missing_documents(self):
        missing = []
        if self.role == 'driver':
            if not self.driver_license:
                missing.append('Driver License')
            if not self.car_license:
                missing.append('Car License')
        if not self.national_id_img:
            missing.append('National ID Image')
        return missing
    #############################Handel naming 
    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"


#############################################################################
class PasswordResetOTP(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    method = models.CharField(max_length=10)  # 'email' or 'phone'

    @classmethod
    def create_for_user(cls, user, method):
        # Delete previous OTPs
        cls.objects.filter(user=user, method=method).delete()

        otp_code = get_random_string(length=6, allowed_chars='0123456789')

        otp = cls.objects.create(
            user=user,
            otp=otp_code,
            expires_at=timezone.now() + timezone.timedelta(minutes=15),
            method=method
        )

        return otp

    def is_valid(self):
        return not self.used and self.expires_at > timezone.now()
    def send_otp_email(self):
        subject = "Your Parking App Password Reset OTP"
        message = f"Your OTP code is: {self.otp}\nThis code expires in 15 minutes."
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.user.email])
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.user.email])

    def send_otp_whatsapp(self):
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        phone = self.user.phone  # تأكد من تنسيقه الصحيح
        message_body = f"Your Parking App OTP is: {self.otp}\nThis code expires in 15 minutes."

        try:
            message = client.messages.create(
                from_=settings.TWILIO_WHATSAPP_NUMBER,    
                to=f'whatsapp:+2{phone}',                   
                body=message_body
            )
            return message.sid
        except Exception as e:
            raise Exception(f"Failed to send WhatsApp message: {str(e)}")
        
        
############# Model to track verification requests and admin actions  #####################

class VerificationRequest(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Verified', 'Verified'),
        ('Rejected', 'Rejected'),
    )
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='verification_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    reason = models.TextField(blank=True, null=True, help_text="Reason for rejection or additional notes")
    reviewed_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_requests',
        limit_choices_to={'is_superuser': True}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Verification Request"
        verbose_name_plural = "Verification Requests"
    
    def __str__(self):
        return f"Verification Request for {self.user.email} - {self.status}"
    
