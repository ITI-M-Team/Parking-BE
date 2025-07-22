from rest_framework import serializers
from booking.models import Booking

# ───────────── BookingDetailSerializer ─────────────

class BookingDetailSerializer(serializers.ModelSerializer):
    # بيانات إضافية للواجهة
    garage_name   = serializers.CharField(source='garage.name', read_only=True)
    parking_spot  = serializers.CharField(source='parking_spot.slot_number', read_only=True)
    spot_id       = serializers.IntegerField(source='parking_spot.id', read_only=True)
    garage_id = serializers.IntegerField(source="garage.id", read_only=True)

    price_per_hour = serializers.DecimalField(
        source='garage.price_per_hour', max_digits=6, decimal_places=2, read_only=True
    )
    wallet_balance = serializers.SerializerMethodField()

    # قيم محسوبة
    waiting_time_minutes  = serializers.SerializerMethodField()
    garage_time_minutes   = serializers.SerializerMethodField()
    total_duration_minutes = serializers.SerializerMethodField()
    actual_cost           = serializers.SerializerMethodField()
    late_alert_sent = serializers.BooleanField(read_only=True)


    class Meta:
        model  = Booking
        fields = [
            'id', 'garage', 'garage_name', 'parking_spot', 'spot_id',
             'estimated_cost', 'price_per_hour',"garage_id",
            'reservation_expiry_time', 'status', 'qr_code_image',
            'confirmation_time', 'start_time', 'end_time',
            'wallet_balance', 'actual_cost',
            'waiting_time_minutes', 'garage_time_minutes', 'total_duration_minutes','late_alert_sent',
        ]

    # helpers
    def _minutes(self, td):
        return int(td.total_seconds() // 60) if td else None

    def get_wallet_balance(self, obj):
        return float(obj.driver.wallet_balance)

    def get_waiting_time_minutes(self, obj):
        return self._minutes(obj.waiting_time)

    def get_garage_time_minutes(self, obj):
        return self._minutes(obj.garage_time)

    def get_total_duration_minutes(self, obj):
        return self._minutes(obj.total_parking_time())

    def get_actual_cost(self, obj):
        return round(obj.actual_cost, 2) if obj.actual_cost is not None else None
# booking/serializers.py
from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from garage.models import Garage, ParkingSpot
from booking.models import Booking


class BookingInitiationSerializer(serializers.Serializer):
    # Fields from frontend input
    garage_id = serializers.IntegerField()
    parking_spot_id = serializers.IntegerField()

    # Calculated fields (readonly)
    estimated_cost = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    grace_period = serializers.IntegerField(read_only=True)

    def validate(self, data):
        request = self.context["request"]
        user = request.user
        garage_id = data["garage_id"]
        spot_id = data["parking_spot_id"]

        # ───── Validate: Garage exists ─────
        try:
            garage = Garage.objects.get(id=garage_id)
        except Garage.DoesNotExist:
            raise serializers.ValidationError({"garage_id": "Garage not found."})

        # ───── Validate: Garage open hours ─────
        now = timezone.localtime().time()
        if not (garage.opening_hour <= now <= garage.closing_hour):
            raise serializers.ValidationError({
                "garage_id": "The garage is currently closed. Booking is not allowed."
            })

        # ───── Validate: Parking spot exists in this garage ─────
        try:
            spot = ParkingSpot.objects.get(id=spot_id, garage=garage)
        except ParkingSpot.DoesNotExist:
            raise serializers.ValidationError({
                "parking_spot_id": "This parking spot does not exist in the selected garage."
            })

        # ───── Validate: Spot availability ─────
        if spot.status != "available":
            raise serializers.ValidationError({
                "parking_spot_id": "This parking spot is currently unavailable."
            })

        # ───── Validate: User doesn't already have active booking ─────
        if Booking.objects.filter(
            driver=user,
            status__in=["pending", "confirmed", "confirmed_late", "awaiting_response"],
            # is_cancelled=False,
            end_time__isnull=True
        ).exists():
            raise serializers.ValidationError({
                "non_field_errors": ["You already have an active booking."]
            })

        # ───── Attach extra calculated values to the validated data ─────
        data["garage"] = garage
        data["spot"] = spot
        data["grace_period"] = garage.reservation_grace_period
        data["estimated_cost"] = garage.price_per_hour

        return data
