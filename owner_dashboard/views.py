from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Count, Q

from accounts.models import CustomUser
from garage.models import Garage, ParkingSpot
from booking.models import Booking
from .serializers import GarageDashboardSerializer, ParkingSpotSerializer

class OwnerDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        if user.role != 'garage_owner':
            return Response(
                {"detail": "You do not have permission to access this dashboard."},
                status=status.HTTP_403_FORBIDDEN
            )

        owned_garages = Garage.objects.filter(owner=user)

        if not owned_garages.exists():
            return Response(
                {"detail": "No garages found for this owner."},
                status=status.HTTP_404_NOT_FOUND
            )

        dashboard_data = []
        for garage in owned_garages:
            serializer = GarageDashboardSerializer(garage)
            dashboard_data.append(serializer.data)

        return Response(dashboard_data, status=status.HTTP_200_OK)

class UpdateSpotAvailabilityAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, garage_id, *args, **kwargs):
        user = request.user

        if user.role != 'garage_owner':
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            garage = Garage.objects.get(id=garage_id, owner=user)
        except Garage.DoesNotExist:
            return Response(
                {"detail": "Garage not found or you do not own this garage."},
                status=status.HTTP_404_NOT_FOUND
            )

        new_available_spots_count = request.data.get('new_available_spots_count')

        if new_available_spots_count is None:
            return Response(
                {"detail": "new_available_spots_count is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            new_available_spots_count = int(new_available_spots_count)
            if new_available_spots_count < 0:
                raise ValueError
        except ValueError:
            return Response(
                {"detail": "new_available_spots_count must be a non-negative integer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        current_available_spots = garage.spots.filter(status='available').count()
        total_spots_in_garage = garage.spots.count()

        if new_available_spots_count > total_spots_in_garage:
            return Response(
                {"detail": f"Cannot set available spots to {new_available_spots_count}. Total spots in garage is {total_spots_in_garage}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_available_spots_count < current_available_spots:
            spots_to_change = current_available_spots - new_available_spots_count
            available_spots_to_occupy = garage.spots.filter(status='available').order_by('?')[:spots_to_change]
            for spot in available_spots_to_occupy:
                spot.status = 'occupied'
                spot.save()
        elif new_available_spots_count > current_available_spots:
            spots_to_change = new_available_spots_count - current_available_spots
            occupied_spots_to_make_available = garage.spots.filter(status='occupied').order_by('?')[:spots_to_change]
            for spot in occupied_spots_to_make_available:
                spot.status = 'available'
                spot.save()

        updated_garage = Garage.objects.get(id=garage_id)
        serializer = GarageDashboardSerializer(updated_garage)

        return Response(serializer.data, status=status.HTTP_200_OK)
