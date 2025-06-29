from django.urls import path
from . import views
from .views import GarageDetailView,GarageSpotsView
urlpatterns = [
    path('api/garages/<int:id>/', GarageDetailView.as_view(), name='garage-detail'),
    path('api/garages/<int:id>/spots/', GarageSpotsView.as_view(), name='garage-spots'),
]