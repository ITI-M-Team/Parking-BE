from django.urls import path
from .views import RegisterView
from .views import CustomTokenObtainPairView
from .views import NearbyGaragesView

urlpatterns = [
    path('register/', RegisterView.as_view(),name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('garages/nearby/', NearbyGaragesView.as_view(), name='nearby-garages'),
    
]
