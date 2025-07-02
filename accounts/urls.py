from django.urls import path

from .views import *

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('user-info/', CurrentUserView.as_view(), name='current_user'),
    path('activate/<uidb64>/<token>/', ActivateUserView.as_view(), name='activate_user'),
    path('garages/nearby/', NearbyGaragesView.as_view(), name='nearby-garages'),


    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/verify/', PasswordResetVerifyView.as_view(), name='password_reset_verify'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]



