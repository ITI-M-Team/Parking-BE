from django.db import models

class Garage(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    opening_hour = models.TimeField()
    closing_hour = models.TimeField()

class GarageReview(models.Model):
    garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField()

class ParkingSpot(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
    ]
    garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='spots')
    slot_number = models.CharField(max_length=10)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='available')