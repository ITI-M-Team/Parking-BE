from django.urls import path
from booking.views import (
    BookingInitiateView,
    BookingDetailView,
    ActiveBookingView,
    CancelBookingView,
    scan_qr_code,
    BookingLateDecisionView,
)

urlpatterns = [
    path('initiate/', BookingInitiateView.as_view(), name='booking-initiate'),
    path('<int:id>/', BookingDetailView.as_view(), name='booking-detail'),
    path('<int:id>/late-decision/', BookingLateDecisionView.as_view(), name='booking-late-decision'),
    path('cancel/<int:booking_id>/', CancelBookingView.as_view(), name='booking-cancel'),
    path('active/', ActiveBookingView.as_view(), name='booking-active'),
    path('scanner/', scan_qr_code, name='qr-scan'),
]
