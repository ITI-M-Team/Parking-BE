from rest_framework import serializers

class ReportRequestSerializer(serializers.Serializer):
    garage_id = serializers.IntegerField()
    email = serializers.EmailField()
