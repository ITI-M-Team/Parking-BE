
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('', include('garage.urls')),  
    path('api/bookings/', include('booking.urls')),
    path('api/owner/', include('owner_dashboard.urls')),
    path('api/reports/', include('reports.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Debug: Print all URLs 
# if settings.DEBUG:
#     from django.urls import get_resolver
#     resolver = get_resolver()
#     print("All registered URLs:")
#     for pattern in resolver.url_patterns:
#         print(f"  {pattern}")