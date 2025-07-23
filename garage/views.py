from django.forms import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.db.models import Avg, Q
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from geopy.distance import geodesic

from booking.models import Booking

from .models import Garage, GarageReview, ParkingSpot
from .serializers import (
    GarageReviewSerializer, GarageSerializer, GarageDetailSerializer,
    ParkingSpotSerializer, GarageRegistrationSerializer,
    GarageUpdateSerializer
)

####################### Garage Detail View #######################

class GarageDetailView(APIView):
    def get(self, request, id):
        try:
            garage = Garage.objects.annotate(
                average_rating=Avg('reviews__rating')
            ).get(id=id)

            # default to 0 if no rating yet
            garage.average_rating = round(garage.average_rating or 0, 1)

            data = GarageDetailSerializer(garage, context={'request': request}).data
            data["number_of_spots"] = garage.spots.count()
            data["average_rating"] = garage.average_rating 
            

            return Response(data)

        except Garage.DoesNotExist:
            return Response({"error": "Garage not found"}, status=status.HTTP_404_NOT_FOUND)


####################### Get Spots in Garage #######################

class GarageSpotsView(APIView):
    def get(self, request, id):
        spots = ParkingSpot.objects.filter(garage_id=id)
        serializer = ParkingSpotSerializer(spots, many=True)
        return Response(serializer.data)

####################### Nearby Garages View #######################

class NearbyGaragesView(generics.ListAPIView):
    serializer_class = GarageSerializer

    def get_queryset(self):
        queryset = Garage.objects.all()
        lat = self.request.query_params.get('lat')
        lon = self.request.query_params.get('lon')
        query = self.request.query_params.get('search')

        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(address__icontains=query))

        if lat and lon:
            user_location = (float(lat), float(lon))
            queryset = sorted(queryset, key=lambda garage: geodesic(user_location, (garage.latitude, garage.longitude)).km)

        return queryset

    def get_serializer_context(self):
        return {'request': self.request}

####################### Register Garage #######################

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

####################### Update Garage #######################

class GarageUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, id):
        garage = get_object_or_404(Garage, id=id, owner=request.user)

        serializer = GarageUpdateSerializer(garage, data=request.data, partial=True)

        if serializer.is_valid():
            updated_instance = serializer.save()
            return Response({
                "detail": "Garage updated successfully.",
                "garage_id": updated_instance.id,
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

####################### Garage Occupancy View #######################

class GarageOccupancyView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, garage_id):
        try:
            garage = Garage.objects.get(id=garage_id)
        except Garage.DoesNotExist:
            return Response({'error': 'Garage not found'}, status=404)

        all_spots = ParkingSpot.objects.filter(garage=garage)
        total_spots = all_spots.count()
        occupied_spots = all_spots.filter(status__in=['reserved', 'occupied']).count()
        available_spots = total_spots - occupied_spots

        return Response({
            'garage_id': garage.id,
            'total_spots': total_spots,
            'occupied_spots': occupied_spots,
            'available_spots': available_spots
        })

####################### Submit Garage Review #######################
# class SubmitGarageReviewView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request, garage_id):
#         garage = get_object_or_404(Garage, id=garage_id)

#         if GarageReview.objects.filter(driver=request.user, garage=garage).exists():
#             return Response({'error': 'You have already submitted a review for this garage.'}, status=400)

#         serializer = GarageReviewSerializer(
#             data=request.data,
#             context={'request': request}
#         )

#         if serializer.is_valid():
#             serializer.save(garage=garage, driver=request.user)
#             return Response(serializer.data, status=status.HTTP_201_CREATED)

#         else:
#            print(serializer.errors)  # 👈 ضروري
#            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GarageReviewCreateView(APIView):
    def post(self, request, garage_id, booking_id):
        try:
            garage = Garage.objects.get(id=garage_id)
            booking = Booking.objects.get(id=booking_id, driver=request.user)

            rating = request.data.get("rating")
            comment = request.data.get("comment", "")

            # منع التقييم المكرر
            if GarageReview.objects.filter(booking=booking).exists():
                return Response({"detail": "You already reviewed this booking."}, status=status.HTTP_400_BAD_REQUEST)

            review =GarageReview.objects.create(
                garage=garage,
                booking=booking,
                driver=request.user,
                rating=rating,
                comment=comment
            )
            serializer = GarageReviewSerializer(review)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Garage.DoesNotExist:
            return Response({"detail": "Garage not found."}, status=status.HTTP_404_NOT_FOUND)
        except Booking.DoesNotExist:
            return Response({"detail": "Booking not found or you do not own this booking."}, status=status.HTTP_404_NOT_FOUND)
