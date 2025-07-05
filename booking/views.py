from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from .models import Booking
from garage.models import ParkingSpot
from .serializers import BookingInitiationSerializer
from .tasks import send_expiry_warning

class BookingInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BookingInitiationSerializer(data=request.data)
        if serializer.is_valid():
            garage_id = serializer.validated_data['garage_id']
            spot_id = serializer.validated_data['parking_spot_id']
            arrival_time = serializer.validated_data['estimated_arrival_time']

            spot = ParkingSpot.objects.get(id=spot_id, garage_id=garage_id)
            garage = spot.garage
            estimated_cost = garage.price_per_hour
            grace_period = garage.reservation_grace_period

            expiry_time = timezone.now() + timedelta(minutes=grace_period)

            spot.status = 'reserved'
            spot.save()

            booking = Booking.objects.create(
                driver=request.user,
                garage=garage,
                parking_spot=spot,
                estimated_arrival_time=arrival_time,
                estimated_cost=estimated_cost,
                reservation_expiry_time=expiry_time,
                status='pending'
            )

            # ✅ Schedule Celery task
            send_expiry_warning.apply_async((booking.id,), countdown=grace_period * 60)

            return Response({
                "booking_id": booking.id,
                "estimated_cost": float(estimated_cost),
                "reservation_expiry_time": expiry_time.isoformat(),
                "status": "success"
            }, status=201)

        return Response(serializer.errors, status=400)
