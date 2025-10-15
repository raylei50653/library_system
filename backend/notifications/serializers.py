from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "message",
            "is_read",
            "created_at",
            "loan",
        ]
        read_only_fields = ["id", "created_at", "loan", "type", "message"]