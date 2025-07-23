from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView 

from .views import *

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('user-info/', CurrentUserView.as_view(), name='current_user'),
    path('activate/<uidb64>/<token>/', ActivateUserView.as_view(), name='activate_user'),
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/verify/', PasswordResetVerifyView.as_view(), name='password_reset_verify'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    ## Reviewer AAdmin URLs
    path('admin/verification-requests/', VerificationRequestListView.as_view(), name='verification-requests'),
    path('admin/verification-requests/<int:request_id>/update/', update_verification_status, name='update-verification'),
    path('admin/verification-stats/', verification_stats, name='verification-stats'),
    
]



