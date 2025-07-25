from django.forms import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.db.models import Avg, Q
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, IsAdminUser
from rest_framework.decorators import api_view, permission_classes
from geopy.distance import geodesic
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail
from django.conf import settings

from booking.models import Booking

from .models import Garage, GarageReview, ParkingSpot, GarageVerificationRequest
from .serializers import (
    GarageReviewSerializer, GarageSerializer, GarageDetailSerializer,
    ParkingSpotSerializer, GarageRegistrationSerializer,
    GarageUpdateSerializer, GarageVerificationRequestSerializer,
    GarageVerificationActionSerializer
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
        # Only show verified garages to public
        queryset = Garage.objects.filter(verification_status='Verified')
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
##########       Send email notification when garage is first submitted        ############3
def send_garage_submission_email(garage):
    subject = 'Garage Registration Submitted - Under Review'
    
    context = {
        'user': garage.owner,
        'garage_name': garage.name,
        'site_name': getattr(settings, 'SITE_NAME', 'Parkly'),
    }
    
    html_message = render_to_string('emails/garage_submission.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [garage.owner.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Failed to send garage submission email: {e}")

class GarageRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'garage_owner':
            return Response({"detail": "Only garage owners can register garages."}, status=403)

        serializer = GarageRegistrationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            garage = serializer.save()         
            
            # Send submission confirmation email
            send_garage_submission_email(garage)
            verification_request = garage.verification_requests.first()
            # Return garage details including verification status
            return Response({
                "detail": "Garage registered successfully.",
                "garage_id": garage.id,
                "verification_status": garage.verification_status,
                "garage_name": garage.name,
                "verification_request_id": verification_request.id
            }, status=201)
        return Response(serializer.errors, status=400)

####################### Update Garage #######################
####################### Send email notification when garage is resubmitted after changes #######################
def send_garage_resubmission_email(garage):
    subject = 'Garage Information Updated - Under Review'
    
    context = {
        'user': garage.owner,
        'garage_name': garage.name,
        'site_name': getattr(settings, 'SITE_NAME', 'Parkly'),
    }
    
    html_message = render_to_string('emails/garage_resubmission.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [garage.owner.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Failed to send garage resubmission email: {e}")

class GarageUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, id):
        garage = get_object_or_404(Garage, id=id, owner=request.user)
        
        # Check if critical fields are being updated (you might want to define these in your model)
        critical_fields = ['contract_document', 'latitude', 'longitude', 'address', 'name']
        old_values = {field: getattr(garage, field) for field in critical_fields if hasattr(garage, field)}

        serializer = GarageUpdateSerializer(garage, data=request.data, partial=True)

        if serializer.is_valid():
            updated_instance = serializer.save()
            
            # Check if critical fields were changed
            new_values = {field: getattr(updated_instance, field) for field in critical_fields if hasattr(updated_instance, field)}
            critical_fields_changed = any(old_values.get(field) != new_values.get(field) for field in critical_fields)
            
            if critical_fields_changed:
                # Set status back to pending and send resubmission email
                updated_instance.verification_status = 'Pending'
                updated_instance.save()
                
                # CREATE NEW VERIFICATION REQUEST FOR RESUBMISSION
                verification_request = GarageVerificationRequest.objects.create(
                    garage=updated_instance,
                    status='Pending'
                )
                
                send_garage_resubmission_email(updated_instance)
            
            return Response({
                "detail": "Garage updated successfully.",
                "garage_id": updated_instance.id,
                "verification_status": updated_instance.verification_status,
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

####################### Garage Occupancy View #######################

class GarageOccupancyView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, garage_id):
        try:
            garage = Garage.objects.get(id=garage_id, owner=request.user)
            
            # Check if garage is verified
            if garage.verification_status != 'Verified':
                return Response({
                    'error': 'Garage must be verified to view occupancy data',
                    'verification_status': garage.verification_status
                }, status=403)
                
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
            'available_spots': available_spots,
            'verification_status': garage.verification_status
        })

####################### Submit Garage Review #######################

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

            review = GarageReview.objects.create(
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


####################### Admin Garage Verification Views #######################

class GarageVerificationRequestListView(generics.ListAPIView):
    serializer_class = GarageVerificationRequestSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = GarageVerificationRequest.objects.select_related(
            'garage', 
            'garage__owner', 
            'reviewed_by'
        ).prefetch_related(
            'garage__spots'
        ).all().order_by('-created_at')
        
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset
    
    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            
            # Add pagination info if needed
            return Response({
                'results': serializer.data,
                'count': queryset.count(),
                'status': 'success'
            })
        except Exception as e:
            print(f"Error in GarageVerificationRequestListView: {e}")
            return Response({
                'error': 'Failed to fetch verification requests',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
##Send email notification to garage owner about verification status
def send_garage_verification_email(garage, verification_status, reason='', is_resubmission=False):
    
    subject_map = {
        'Verified': 'Garage Verified - Congratulations!',
        'Rejected': 'Garage Verification Rejected',
        'Pending': 'Garage Under Review'
    }
    
    if is_resubmission and verification_status == 'Pending':
        subject = 'Garage Information Resubmission Received - Under Review'
    else:
        subject = subject_map.get(verification_status, 'Garage Status Update')
    
    context = {
        'user': garage.owner,
        'garage_name': garage.name,
        'status': verification_status,
        'reason': reason,
        'is_resubmission': is_resubmission,
        'site_name': getattr(settings, 'SITE_NAME', 'Smart Parking'),
    }
    
    html_message = render_to_string('emails/garage_verification_status.html', context)
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [garage.owner.email],
        html_message=html_message,
        fail_silently=False,
    )

@api_view(['POST'])
@permission_classes([IsAdminUser])
def update_garage_verification_status(request, request_id):
    try:
        verification_request = get_object_or_404(GarageVerificationRequest, id=request_id)
        serializer = GarageVerificationActionSerializer(data=request.data)
        
        if serializer.is_valid():
            new_status = serializer.validated_data['status']
            reason = serializer.validated_data.get('reason', '')
            
            old_status = verification_request.status
            
            # CRITICAL FIX: Update garage verification status FIRST
            garage = verification_request.garage
            garage.verification_status = new_status
            garage.save()
            
            # Then update verification request
            verification_request.status = new_status
            verification_request.reason = reason
            verification_request.reviewed_by = request.user
            verification_request.save()
            
            # DEBUG: Add logging to verify the update
            print(f"🔧 Updated garage {garage.id} ({garage.name}) status to: {garage.verification_status}")
            
            # Verify the update worked by fetching fresh from DB
            updated_garage = Garage.objects.get(id=garage.id)
            print(f"🔧 Verified garage status in DB: {updated_garage.verification_status}")
            
            # Send email notification
            send_garage_verification_email(garage, new_status, reason)
            
            return Response({
                'message': 'Garage verification status updated successfully',
                'status': new_status,
                'garage_name': garage.name,
                'owner_email': garage.owner.email,
                'previous_status': old_status,
                'garage_id': garage.id,
                'db_status': updated_garage.verification_status  # Add for debugging
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        print(f"❌ Error updating garage verification status: {e}")
        import traceback
        traceback.print_exc()
        return Response({
            'error': 'Failed to update verification status',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAdminUser])
def garage_verification_stats(request):
    try:
        total_requests = GarageVerificationRequest.objects.count()
        pending_requests = GarageVerificationRequest.objects.filter(status='Pending').count()
        verified_requests = GarageVerificationRequest.objects.filter(status='Verified').count()
        rejected_requests = GarageVerificationRequest.objects.filter(status='Rejected').count()

        # Count resubmissions (requests that had a reason before)
        resubmission_count = GarageVerificationRequest.objects.filter(
            status='Pending',
            reason__isnull=False  
        ).count()

        return Response({
            'total_requests': total_requests,
            'pending_requests': pending_requests,
            'verified_requests': verified_requests,
            'rejected_requests': rejected_requests,
            'resubmission_count': resubmission_count,
            'verification_rate': (verified_requests / total_requests * 100) if total_requests > 0 else 0
        })
    except Exception as e:
        print(f"Error fetching garage verification stats: {e}")
        return Response({
            'error': 'Failed to fetch verification stats',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

####################### Owner's Garage List View #######################

class OwnerGarageListView(generics.ListAPIView):
    serializer_class = GarageDetailSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Garage.objects.filter(owner=self.request.user).order_by('-created_at')
    
    def get_serializer_context(self):
        return {'request': self.request}
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # 🔍 DEBUG: Print garage verification statuses
        print("🔍 DEBUG: Garage verification statuses:")
        for garage in queryset:
            print(f"  - {garage.name}: {garage.verification_status}")
        
        serializer = self.get_serializer(queryset, many=True)
        
        # 🔍 DEBUG: Print serialized data
        print("🔍 DEBUG: Serialized data:")
        for garage_data in serializer.data:
            print(f"  - {garage_data.get('name', 'Unknown')}: {garage_data.get('verification_status', 'MISSING')}")
        
        # Add verification statistics
        total_garages = queryset.count()
        verified_garages = queryset.filter(verification_status='Verified').count()
        pending_garages = queryset.filter(verification_status='Pending').count()
        rejected_garages = queryset.filter(verification_status='Rejected').count()
        
        return Response({
            'results': serializer.data,
            'statistics': {
                'total': total_garages,
                'verified': verified_garages,
                'pending': pending_garages,
                'rejected': rejected_garages
            }
        })
    
##Add new view to check garage verification status
class GarageVerificationStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, garage_id):
        try:
            garage = Garage.objects.get(id=garage_id, owner=request.user)
            
            # Get the latest verification request
            latest_request = garage.verification_requests.first()
            
            return Response({
                'garage_id': garage.id,
                'garage_name': garage.name,
                'verification_status': garage.verification_status,
                'created_at': latest_request.created_at if latest_request else garage.created_at,
                'reason': latest_request.reason if latest_request else None,
                'can_edit': garage.verification_status in ['Rejected', 'Pending']
            })
        except Garage.DoesNotExist:
            return Response({"error": "Garage not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error fetching garage verification status: {e}")
            return Response({
                "error": "Failed to fetch verification status",
                "detail": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class OwnerDashboardDataView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Get user's garages with proper verification status
            # Remove the invalid 'created_at' ordering - use 'id' instead
            garages = Garage.objects.filter(owner=request.user).order_by('-id')
            
            # DEBUG: Print verification statuses
            print("🔧 Owner Dashboard - Garage statuses:")
            for garage in garages:
                print(f"  - {garage.name}: {garage.verification_status}")
            
            garage_data = []
            for garage in garages:
                # Get today's bookings
                from datetime import date
                from booking.models import Booking
                
                today_bookings = Booking.objects.filter(
                    parking_spot__garage=garage,
                    start_time__date=date.today()
                ).select_related('driver', 'parking_spot')
                
                # Calculate spots counts
                all_spots = garage.spots.all()
                available_spots = all_spots.filter(status='available').count()
                occupied_spots = all_spots.filter(status__in=['occupied', 'reserved']).count()
                
                # Calculate today's revenue
                today_revenue = sum(
                    booking.actual_cost for booking in today_bookings
                    if booking.actual_cost
                )
                
                # Check if garage is currently open (calculate from hours)
                from datetime import datetime
                now = datetime.now().time()
                is_open = True  # Default to open if no hours specified
                if garage.opening_hour and garage.closing_hour:
                    is_open = garage.opening_hour <= now <= garage.closing_hour
                
                garage_info = {
                    'id': garage.id,
                    'name': garage.name,
                    'address': garage.address,
                    'verification_status': garage.verification_status,  # CRITICAL
                    'is_open': is_open,
                    'opening_hour': garage.opening_hour,
                    'closing_hour': garage.closing_hour,
                    'available_spots_count': available_spots,
                    'occupied_spots_count': occupied_spots,
                    'today_revenue': float(today_revenue) if today_revenue else 0.0,
                    'today_bookings': [
                        {
                            'id': booking.id,
                            'driver_name': f"{booking.driver.first_name} {booking.driver.last_name}".strip() or booking.driver.username,
                            'spot_number': booking.parking_spot.slot_number,
                            'start_time': booking.start_time,
                            'end_time': booking.end_time,
                            'total_price': booking.actual_cost,
                            'status': booking.status
                        }
                        for booking in today_bookings
                    ],
                    'spots': [
                        {
                            'id': spot.id,
                            'slot_number': spot.slot_number,
                            'status': spot.status
                        }
                        for spot in all_spots
                    ]
                }
                garage_data.append(garage_info)
            
            # DEBUG: Print final garage data structure
            print("🔧 Final garage data being returned:")
            for garage_info in garage_data:
                print(f"  - {garage_info['name']}: verification_status = {garage_info['verification_status']}")
            
            return Response(garage_data)
            
        except Exception as e:
            print(f"❌ Error in OwnerDashboardDataView: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                'error': 'Failed to fetch dashboard data',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)