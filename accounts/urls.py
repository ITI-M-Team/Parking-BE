from django.urls import path
from .views import (
    RegisterView,
    CustomTokenObtainPairView,
    CurrentUserView,
    ActivateUserView,
    NearbyGaragesView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('user-info/', CurrentUserView.as_view(), name='current_user'),
    path('activate/<uidb64>/<token>/', ActivateUserView.as_view(), name='activate_user'),
    path('garages/nearby/', NearbyGaragesView.as_view(), name='nearby-garages'),
]
