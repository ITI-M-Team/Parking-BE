# booking/urls.py
from django.urls import path
from .views import BookingInitiateView, BookingRetrieveView

urlpatterns = [
    path('initiate/', BookingInitiateView.as_view(), name='booking-initiate'),
    path('<int:pk>/', BookingRetrieveView.as_view(), name='booking-detail'),  # ← this is what your React needs
]
