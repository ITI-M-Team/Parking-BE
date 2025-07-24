# payment/views.py

import requests
import time
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
from accounts.models import CustomUser # تأكد من أن هذا هو المسار الصحيح لموديل المستخدم

class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        amount_str = request.data.get("amount")
        payment_method = request.data.get("payment_method") # "card" or "wallet"

        # --- نقطة تفتيش للتشخيص (يمكن حذفها بعد التأكد من أنها تعمل) ---
        print(f"✅ [BACKEND-LOG] Received payment method: '{payment_method}'")

        # --- اختيار الـ Integration ID بناءً على طلب الفرونت إند ---
        integration_id = None
        if payment_method == "card":
            integration_id = settings.PAYMOB_INTEGRATION_ID_CARD
        elif payment_method == "wallet":
            integration_id = settings.PAYMOB_INTEGRATION_ID_WALLET
        
        if not integration_id:
            return Response({"error": "Invalid payment method selected."}, status=400)

        try:
            amount_decimal = Decimal(amount_str)
            if amount_decimal <= 0:
                raise ValueError("Amount must be positive.")
            amount_cents = int(amount_decimal * 100)
        except (ValueError, TypeError):
            return Response({"error": "Invalid amount provided."}, status=400)

        # 1. Authentication Request
        try:
            auth_response = requests.post(
                "https://accept.paymob.com/api/auth/tokens",
                json={"api_key": settings.PAYMOB_API_KEY}
             )
            auth_response.raise_for_status()
            auth_token = auth_response.json().get("token")
        except requests.RequestException as e:
            return Response({"error": f"Paymob auth failed: {e}"}, status=503)

        # 2. Order Registration Request
        order_payload = {
            "auth_token": auth_token,
            "delivery_needed": "false",
            "amount_cents": str(amount_cents),
            "currency": "EGP",
            "merchant_order_id": f"wallet-{user.id}-{int(time.time())}",
        }
        try:
            order_response = requests.post(
                "https://accept.paymob.com/api/ecommerce/orders",
                json=order_payload
             )
            order_response.raise_for_status()
            order_id = order_response.json().get("id")
        except requests.RequestException as e:
            return Response({"error": f"Paymob order creation failed: {e}"}, status=503)

        # 3. Payment Key Request
        payment_key_payload = {
            "auth_token": auth_token,
            "amount_cents": str(amount_cents),
            "expiration": 3600,
            "order_id": order_id,
            "billing_data": {
                "email": user.email or "NA", "first_name": user.username or "NA", "last_name": "NA",
                "phone_number": user.phone or "NA", "street": "NA", "building": "NA",
                "floor": "NA", "apartment": "NA", "city": "NA", "country": "NA",
                "postal_code": "NA", "state": "NA"
            },
            "currency": "EGP",
            "integration_id": integration_id
        }
        try:
            payment_key_response = requests.post(
                "https://accept.paymob.com/api/acceptance/payment_keys",
                json=payment_key_payload
             )
            payment_key_response.raise_for_status()
            payment_key = payment_key_response.json().get("token")
        except requests.RequestException as e:
            return Response({"error": f"Paymob payment key failed: {e}"}, status=503)

        # --- الكود الموحد: استخدم دائمًا رابط الـ iFrame ---
        payment_url = f"https://accept.paymob.com/api/acceptance/iframes/{settings.PAYMOB_IFRAME_ID}?payment_token={payment_key}"        
        # أرسل دائمًا النوع "iframe" للفرونت إند
        return Response({"payment_url": payment_url, "type": "iframe"} )


class PaymentCallbackView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data.get("obj")
        
        # في بيئة الإنتاج، يجب التحقق من HMAC هنا لضمان الأمان
        
        if data and data.get("success") == True:
            order_id_str = data.get("order", {}).get("merchant_order_id")
            amount_cents = data.get("amount_cents")
            
            try:
                _, user_id, _ = order_id_str.split('-')
                user = CustomUser.objects.get(id=int(user_id))
                
                amount_egp = Decimal(amount_cents) / 100
                user.wallet_balance += amount_egp
                user.save(update_fields=["wallet_balance"])
                
                print(f"✅ SUCCESS: Wallet for user {user.email} topped up with {amount_egp} EGP.")

            except (ValueError, CustomUser.DoesNotExist) as e:
                print(f"❌ ERROR processing callback: {e}")
        
        else:
            print("ℹ️ Callback received for a FAILED or PENDING transaction.")

        return Response({"status": "ok"}, status=200)
