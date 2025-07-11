from django.urls import path
from .views import BookingInitiateView, BookingDetailView  # أو BookingRetrieveView حسب الكود النهائي

urlpatterns = [
    path('initiate/', BookingInitiateView.as_view(), name='booking-initiate'),
    path('<int:id>/', BookingDetailView.as_view(), name='booking-detail'),
]
