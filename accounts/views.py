
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from .models import CustomUser, Garage
from .serializers import RegisterSerializer, CustomTokenObtainPairSerializer, GarageSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from geopy.distance import geodesic
from django.db.models import Q


 



class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def perform_create(self, serializer):
        driver_license = serializer.validated_data.pop('driver_license', None)
        car_license = serializer.validated_data.pop('car_license', None)
        national_id_img = serializer.validated_data.pop('national_id_img', None)

        validated_data = serializer.validated_data
        validated_data['password'] = make_password(validated_data['password'])
        validated_data['verification_status'] = 'Pending'

        user = CustomUser.objects.create(**validated_data)

        if driver_license:
            user.driver_license = driver_license
        if car_license:
            user.car_license = car_license
        if national_id_img:
            user.national_id_img = national_id_img

        user.save()


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


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


