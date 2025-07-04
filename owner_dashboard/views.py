from django.shortcuts import render

# Create your views here.
# owner_dashboard/views.py

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

        # 1. التحقق من أن المستخدم هو مالك جراج
        if user.role != 'garage_owner':
            return Response(
                {"detail": "You do not have permission to access this dashboard."},
                status=status.HTTP_403_FORBIDDEN
            )

        # 2. جلب الجراجات التي يمتلكها المستخدم
        # هذا يتطلب أن يكون هناك حقل 'owner' في Garage model يربط الجراج بمالكه
        # تأكد من أنك قمت بتعديل garage/models.py كما هو موضح في الخطوة 0
        owned_garages = Garage.objects.filter(owner=user)

        if not owned_garages.exists():
            return Response(
                {"detail": "No garages found for this owner."},
                status=status.HTTP_404_NOT_FOUND
            )

        # يمكن للمالك أن يمتلك أكثر من جراج، لذا سنقوم بمعالجة كل جراج
        # إذا كنت تتوقع جراجًا واحدًا فقط لكل مالك، يمكنك تعديل هذا المنطق
        dashboard_data = []
        for garage in owned_garages:
            serializer = GarageDashboardSerializer(garage)
            dashboard_data.append(serializer.data)

        return Response(dashboard_data, status=status.HTTP_200_OK)

class UpdateSpotAvailabilityAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, garage_id, *args, **kwargs):
        user = request.user

        # 1. التحقق من أن المستخدم هو مالك جراج
        if user.role != 'garage_owner':
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN
            )

        # 2. جلب الجراج والتأكد من أن المالك الحالي هو مالكه
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

        # 3. تحديث عدد الأماكن المتاحة
        # هذا المنطق يفترض أنك تقوم بتحديث عدد الأماكن المتاحة مباشرة
        # وليس تغيير حالة كل مكان على حدة.
        # إذا كنت تدير كل ParkingSpot بشكل فردي، ستحتاج إلى منطق أكثر تعقيدًا هنا
        # لتغيير حالة عدد معين من الأماكن إلى 'available' أو 'occupied'.
        # على سبيل المثال، يمكنك جعل عدد معين من الأماكن 'available' والباقي 'occupied'
        # بناءً على العدد الجديد.
        # للتوضيح، سأفترض أننا نعدل عدد الأماكن المتاحة بشكل عام في الجراج.
        # إذا كان لديك حقل 'total_spots' في Garage model، يمكنك استخدامه هنا.

        # مثال بسيط: إذا كان لديك حقل 'available_spots' في Garage model
        # garage.available_spots = new_available_spots_count
        # garage.save()

        # بما أنك لا تملك حقل 'available_spots' مباشر في Garage model،
        # سنقوم بتعديل عدد الأماكن المتاحة/المشغولة بناءً على الطلب.
        # هذا يتطلب منطقًا أكثر تعقيدًا لتحديد أي الأماكن يجب تغيير حالتها.
        # أفضل طريقة هي أن يكون لديك حقل 'total_spots' في Garage model
        # ثم تقوم بتعديل عدد الأماكن المتاحة بناءً على ذلك.

        # مؤقتًا، سأقدم حلاً يعتمد على تغيير حالة ParkingSpot بشكل مباشر
        # ولكن هذا قد لا يكون الأمثل إذا كان لديك عدد كبير من الأماكن.
        # الأفضل هو أن يكون لديك حقل 'total_spots' في Garage model
        # وتستخدمه لحساب الأماكن المتاحة.

        # هذا الجزء يحتاج إلى توضيح أكثر منك حول كيفية إدارة "تعديل الأماكن المتاحة"
        # هل هو تحديث لعدد الأماكن المتاحة كقيمة مجردة؟
        # أم هو تغيير حالة ParkingSpot الفردية؟

        # إذا كان القصد هو تحديث عدد الأماكن المتاحة كقيمة مجردة (مثلاً، إذا كان لديك حقل `available_spots_count` في `Garage` model):
        # garage.available_spots_count = new_available_spots_count
        # garage.save()

        # إذا كان القصد هو تغيير حالة ParkingSpot الفردية:
        # هذا يتطلب منطقًا معقدًا لتحديد أي الأماكن يجب أن تصبح متاحة أو غير متاحة.
        # على سبيل المثال، يمكنك جعل أول `new_available_spots_count` من الأماكن متاحة، والباقي مشغول.
        # هذا ليس عمليًا دائمًا.

        # **لغرض هذه المهمة، سأفترض أنك تريد تحديث عدد الأماكن المتاحة كقيمة مجردة.**
        # **ولكن بما أن Garage model لا يحتوي على حقل `available_spots_count`،**
        # **فإن هذا الـ API يحتاج إلى تعديل في الـ model أو توضيح منك.**

        # **الحل البديل (إذا لم يكن لديك حقل `available_spots_count` في Garage model):**
        # يمكنك تحديث حالة عدد معين من الـ ParkingSpot objects.
        # هذا مثال على كيفية تحديث عدد معين من الأماكن لتكون 'available'
        # وتغيير الباقي إلى 'occupied' (إذا كان العدد الجديد أقل من الحالي)
        # أو العكس (إذا كان العدد الجديد أكبر من الحالي).
        # هذا المنطق معقد ويجب أن يتم بحذر لتجنب التضارب مع الحجوزات.

        # **أفضل حل هو إضافة حقل `total_spots` إلى Garage model**
        # **ثم حساب `available_spots` بناءً على `total_spots` وعدد الأماكن المشغولة/المحجوزة.**

        # **لغرض الاستمرارية مع الخطة، سأقوم بتنفيذ هذا الـ API بناءً على افتراض أنك ستضيف حقل `total_spots` إلى Garage model.**
        # **وأن هذا الـ API سيقوم بتعديل عدد الأماكن المتاحة بناءً على هذا الحقل.**

        # **إذا لم يكن لديك حقل `total_spots`، فإن هذا الـ API لن يعمل كما هو متوقع.**

        # **تحديث: بما أن `ParkingSpot` model يحتوي على `status`، يمكننا تعديل حالة الأماكن مباشرة.**
        # **ولكن "تعديل عدد الأماكن المتاحة" يعني عادةً تغيير عدد الأماكن التي يمكن حجزها.**
        # **هذا يتطلب منطقًا يغير حالة الـ `ParkingSpot` objects.**

        # **لتبسيط الأمر، سأفترض أن `new_available_spots_count` هو العدد الذي تريده من الأماكن المتاحة.**
        # **وسنقوم بتغيير حالة الـ `ParkingSpot` objects لتتوافق مع هذا العدد.**

        current_available_spots = garage.spots.filter(status='available').count()
        current_occupied_or_reserved_spots = garage.spots.filter(Q(status='occupied') | Q(status='reserved')).count()
        total_spots_in_garage = garage.spots.count()

        if new_available_spots_count > total_spots_in_garage:
            return Response(
                {"detail": f"Cannot set available spots to {new_available_spots_count}. Total spots in garage is {total_spots_in_garage}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_available_spots_count < current_available_spots:
            # نحتاج إلى جعل بعض الأماكن "غير متاحة"
            spots_to_change = current_available_spots - new_available_spots_count
            # اختر الأماكن المتاحة التي لم يتم حجزها بعد لتغيير حالتها
            available_spots_to_occupy = garage.spots.filter(status='available').order_by('?')[:spots_to_change]
            for spot in available_spots_to_occupy:
                spot.status = 'occupied' # أو أي حالة أخرى مناسبة لـ "غير متاح"
                spot.save()
        elif new_available_spots_count > current_available_spots:
            # نحتاج إلى جعل بعض الأماكن "متاحة"
            spots_to_change = new_available_spots_count - current_available_spots
            # اختر الأماكن "المشغولة" أو "المحجوزة" التي يمكن جعلها متاحة
            # هذا الجزء يحتاج إلى منطق دقيق لتجنب إلغاء حجوزات قائمة
            # هنا نفترض أننا نغير حالة الأماكن التي ليست 'available' إلى 'available'
            # ولكن يجب أن تكون حذرًا جدًا مع الأماكن 'reserved'
            # الأفضل هو أن يكون لديك نوع آخر من الحالة مثل 'maintenance' أو 'unavailable_by_owner'
            # لغرض هذا المثال، سأفترض أننا نغير الأماكن 'occupied' إلى 'available'
            occupied_spots_to_make_available = garage.spots.filter(status='occupied').order_by('?')[:spots_to_change]
            for spot in occupied_spots_to_make_available:
                spot.status = 'available'
                spot.save()

        # إعادة جلب بيانات الجراج بعد التحديث لضمان الدقة
        updated_garage = Garage.objects.get(id=garage_id)
        serializer = GarageDashboardSerializer(updated_garage)

        return Response(serializer.data, status=status.HTTP_200_OK)

