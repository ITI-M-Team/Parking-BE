from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ReportRequestSerializer
from .utils import generate_and_send_report

class GenerateWeeklyReportAPIView(APIView):
    def post(self, request):
        serializer = ReportRequestSerializer(data=request.data)
        if serializer.is_valid():
            garage_id = serializer.validated_data['garage_id']
            email = serializer.validated_data['email']
            try:
                generate_and_send_report(garage_id, email)
                return Response({"message": "Report sent successfully."})
            except Exception as e:
                return Response({"error": str(e)}, status=500)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
