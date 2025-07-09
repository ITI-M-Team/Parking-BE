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
from .utils import generate_qr_code_for_booking
User = get_user_model()


class BookingInitiateView(APIView):
    def post(self, request):
        serializer = BookingInitiationSerializer(data=request.data)
        if serializer.is_valid():
            garage = serializer.validated_data['garage']
            spot = serializer.validated_data['spot']
            arrival_time = serializer.validated_data['estimated_arrival_time']

            dummy_user = User.objects.first()

            # Save booking - expiry time handled by model's save()
            spot.status = 'reserved'
            spot.save()

            booking = Booking.objects.create(
                driver=dummy_user,
                garage=garage,
                parking_spot=spot,
                estimated_arrival_time=arrival_time,
                status='pending'
            )
            
            generate_qr_code_for_booking(booking)

            send_expiry_warning.apply_async((booking.id,), eta=booking.reservation_expiry_time)

            return Response({
                "booking_id": booking.id,
                "reservation_expiry_time": booking.reservation_expiry_time.isoformat(),
                "status": "success"
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BookingRetrieveView(RetrieveAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingDetailSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'id' 

