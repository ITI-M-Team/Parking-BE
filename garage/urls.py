from django.urls import path
from .views import *

urlpatterns = [
    path('api/garages/<int:id>/', GarageDetailView.as_view(), name='garage-detail'),
    path('api/garages/<int:id>/spots/', GarageSpotsView.as_view(), name='garage-spots'),
    path('api/garages/nearby/', NearbyGaragesView.as_view(), name='nearby-garages'),
    path('api/garages/register/', GarageRegisterView.as_view(), name='garage-register'),
    path('api/garages/<int:id>/update/', GarageUpdateView.as_view(), name='garage-update'),
    path('api/garages/<int:garage_id>/occupancy/', garage_occupancy_view, name='garage-occupancy'),
]
