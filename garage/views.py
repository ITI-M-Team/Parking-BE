from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.db.models import Q
from geopy.distance import geodesic
from .models import Garage, ParkingSpot
from .serializers import GarageSerializer, GarageDetailSerializer, ParkingSpotSerializer


class GarageDetailView(APIView):
    def get(self, request, id):
        try:
            garage = Garage.objects.get(id=id)
            serializer = GarageDetailSerializer(garage, context={'request': request})
            return Response(serializer.data)
        except Garage.DoesNotExist:
            return Response({"error": "Garage not found"}, status=status.HTTP_404_NOT_FOUND)


class GarageSpotsView(APIView):
    def get(self, request, id):
        spots = ParkingSpot.objects.filter(garage_id=id)
        serializer = ParkingSpotSerializer(spots, many=True)
        return Response(serializer.data)


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
