
from django.urls import path
from .views import OwnerDashboardAPIView, UpdateSpotAvailabilityAPIView

urlpatterns = [
    path('dashboard/', OwnerDashboardAPIView.as_view(), name='owner_dashboard'),
    path('garages/<int:garage_id>/update-spots/', UpdateSpotAvailabilityAPIView.as_view(), name='update_spot_availability'),
]
