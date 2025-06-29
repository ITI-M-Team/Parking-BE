from django.urls import path
from .views import RegisterView
from .views import CustomTokenObtainPairView,ActivateUserView

urlpatterns = [
    path('register/', RegisterView.as_view(),name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('activate/<uidb64>/<token>/', ActivateUserView.as_view(), name='activate_user'),
]


