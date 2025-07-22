from django.urls import path
from .views import GenerateWeeklyReportAPIView

urlpatterns = [
    path('weekly/', GenerateWeeklyReportAPIView.as_view(), name='generate-report'),
]
