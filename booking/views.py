# booking/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from .models import Booking
from garage.models import ParkingSpot
from .serializers import BookingInitiationSerializer, BookingDetailSerializer
from .tasks import send_expiry_warning

User = get_user_model()


class BookingInitiateView(APIView):
    def post(self, request):
        serializer = BookingInitiationSerializer(data=request.data)
        if serializer.is_valid():
            garage = serializer.validated_data['garage']
            spot = serializer.validated_data['spot']
            arrival_time = serializer.validated_data['estimated_arrival_time']
            grace_period = garage.reservation_grace_period
            expiry_time = arrival_time + timedelta(minutes=grace_period)

            # Dummy user for now
            dummy_user = User.objects.first()

            spot.status = 'reserved'
            spot.save()

            booking = Booking.objects.create(
                driver=dummy_user,
                garage=garage,
                parking_spot=spot,
                estimated_arrival_time=arrival_time,
                reservation_expiry_time=expiry_time,
                status='pending'
            )

            send_expiry_warning.apply_async((booking.id,), eta=expiry_time)

            return Response({
                "booking_id": booking.id,
                "reservation_expiry_time": expiry_time.isoformat(),
                "status": "success"
            }, status=201)

        return Response(serializer.errors, status=400)


class BookingRetrieveView(RetrieveAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingDetailSerializer
