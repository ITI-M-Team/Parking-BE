from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Avg
from django.db.models import Q
from .serializers import GarageSerializer
from rest_framework.permissions import IsAuthenticated

from rest_framework import generics
from .models import Garage, ParkingSpot
from .serializers import *
from geopy.distance import geodesic
from rest_framework.decorators import api_view, permission_classes



class GarageDetailView(APIView):
    def get(self, request, id):
        try:
            garage = Garage.objects.annotate(
                average_rating=Avg('reviews__rating')
            ).get(id=id)
            serializer = GarageDetailSerializer(garage, context={'request': request})
            return Response(serializer.data)
        except Garage.DoesNotExist:
            return Response({"error": "Garage not found"}, status=status.HTTP_404_NOT_FOUND)


class GarageSpotsView(APIView):
    def get(self, request, id):
        spots = ParkingSpot.objects.filter(garage_id=id)
        serializer = ParkingSpotSerializer(spots, many=True)
        return Response(serializer.data)
    


# Nearby Garages View
class NearbyGaragesView(generics.ListAPIView):
    serializer_class = GarageSerializer

    def get_queryset(self):
        queryset = Garage.objects.all()
        lat = self.request.query_params.get('lat')
        lon = self.request.query_params.get('lon')
        query = self.request.query_params.get('search')

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(address__icontains=query)
            )

        if lat and lon:
            user_location = (float(lat), float(lon))
            queryset = sorted(
                queryset,
                key=lambda garage: geodesic(
                    user_location,
                    (garage.latitude, garage.longitude)
                ).km
            )

        return queryset

    def get_serializer_context(self):
        return {'request': self.request}
############## add garage data ######################
class GarageRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'garage_owner':
            return Response({"detail": "Only garage owners can register garages."}, status=403)

        serializer = GarageRegistrationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            garage = serializer.save()
            return Response({"detail": "Garage registered successfully.", "garage_id": garage.id}, status=201)
        return Response(serializer.errors, status=400)
###############end add garage data ######################
##############update garage data ######################
class GarageUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, id):
        try:
            garage = Garage.objects.get(id=id)
        except Garage.DoesNotExist:
            return Response({"error": "Garage not found."}, status=404)

        if request.user != garage.owner:
            return Response({"error": "You can only update your own garage."}, status=403)

        serializer = GarageUpdateSerializer(garage, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
###############end update garage data ######################
###############realtime occupancy ######################
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def garage_occupancy_view(request, garage_id):
    try:
        garage = Garage.objects.get(id=garage_id)
    except Garage.DoesNotExist:
        return Response({"error": "Garage not found."}, status=status.HTTP_404_NOT_FOUND)

    # Only the owner can view the occupancy of their garage
    if request.user != garage.owner:
        return Response({"error": "You can only view your own garage occupancy."}, status=403)

    total = garage.spots.count()
    occupied = garage.spots.filter(status='occupied').count()
    available = garage.spots.filter(status='available').count()
    reserved = garage.spots.filter(status='reserved').count()

    return Response({
        "garage_id": garage.id,
        "garage_name": garage.name,
        "total_spots": total,
        "occupied_spots": occupied,
        "available_spots": available,
        "reserved_spots": reserved
    })
###############end realtime occupancy ######################