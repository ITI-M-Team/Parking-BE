from django.urls import path
from .views import BookingInitiateView, BookingDetailView  # أو BookingRetrieveView حسب الكود النهائي
from .views import CancelBookingView
from .views import ActiveBookingView
from .views import scan_qr_code
urlpatterns = [
    path('initiate/', BookingInitiateView.as_view(), name='booking-initiate'),
    path('<int:id>/', BookingDetailView.as_view(), name='booking-detail'),
    path('cancel/<int:booking_id>/', CancelBookingView.as_view(), name='booking-cancel'),
    path('active/', ActiveBookingView.as_view(), name='booking-active'),
    path('scanner/', scan_qr_code, name='qr-scan'),
]
