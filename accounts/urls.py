from django.urls import path
from .views import CurrentUserView, RegisterView
from .views import CustomTokenObtainPairView
from .views import RegisterView
from .views import CustomTokenObtainPairView,ActivateUserView


urlpatterns = [
    path('register/', RegisterView.as_view(),name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),

    path('user-info/', CurrentUserView.as_view(), name='current_user'),

    path('activate/<uidb64>/<token>/', ActivateUserView.as_view(), name='activate_user'),

]


