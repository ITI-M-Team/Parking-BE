
from django.urls import path
from .views import InitiatePaymentView, PaymentCallbackView

app_name = 'payment'

urlpatterns = [
    path('initiate/', InitiatePaymentView.as_view(), name='initiate-payment'),
    path('callback/', PaymentCallbackView.as_view(), name='payment-callback'),
]
