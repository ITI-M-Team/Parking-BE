from django.urls import path
from .views import *

urlpatterns = [
    path('api/garages/<int:id>/', GarageDetailView.as_view(), name='garage-detail'),
    path('api/garages/<int:id>/spots/', GarageSpotsView.as_view(), name='garage-spots'),
    path('api/garages/nearby/', NearbyGaragesView.as_view(), name='nearby-garages'),
    path('api/garages/register/', GarageRegisterView.as_view(), name='garage-register'),
    path('api/garages/<int:id>/update/', GarageUpdateAPIView.as_view(), name='garage-update'),
    path('api/garages/<int:garage_id>/occupancy/', GarageOccupancyView.as_view(), name='garage-occupancy'),
    path('api/garages/<int:garage_id>/review/<int:booking_id>/', GarageReviewCreateView.as_view(), name='garage-review'),

    # New garage verification endpoints
    path('api/garages/verification-requests/', GarageVerificationRequestListView.as_view(), name='garage-verification-requests'),
    path('api/garages/verification-requests/<int:request_id>/update/', update_garage_verification_status, name='update-garage-verification-status'),
    path('api/garages/verification-stats/', garage_verification_stats, name='garage-verification-stats'),
    
    # verification status endpoint
    path('api/garages/<int:garage_id>/verification-status/', GarageVerificationStatusView.as_view(), name='garage-verification-status'),
    # Owner's garage management
    path('api/garages/my-garages/', OwnerGarageListView.as_view(), name='owner-garages'),
    path('api/owner/dashboard/', OwnerDashboardDataView.as_view(), name='owner-dashboard-data'),
]
