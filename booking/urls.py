# booking/urls.py
from django.urls import path
from .views import BookingInitiateView, BookingRetrieveView

urlpatterns = [
    path('initiate/', BookingInitiateView.as_view(), name='booking-initiate'),
    path("<int:id>/", BookingRetrieveView.as_view(), name="booking-detail")  # ✅ فقط <int:id> بدون 'bookings/'
]
