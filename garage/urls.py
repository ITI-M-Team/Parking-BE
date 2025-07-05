from django.urls import path
from .views import *

urlpatterns = [
    path('api/garages/<int:id>/', GarageDetailView.as_view(), name='garage-detail'),
    path('api/garages/<int:id>/spots/', GarageSpotsView.as_view(), name='garage-spots'),
    path('api/garages/nearby/', NearbyGaragesView.as_view(), name='nearby-garages'),
    path('api/garages/register/', GarageRegisterView.as_view(), name='garage-register'),
]
