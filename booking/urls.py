from django.urls import path
from .views import BookingInitiateView

urlpatterns = [
    path('initiate/', BookingInitiateView.as_view(), name='booking-initiate'),
]
