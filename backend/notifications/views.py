from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer
from .services import mark_as_read, mark_all_as_read


class NotificationListView(generics.ListAPIView):
    """列出目前登入者的通知；支援 ?is_read=true/false 篩選"""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        is_read = self.request.query_params.get("is_read")
        if is_read is not None:
            if is_read.lower() in {"true", "1", "yes"}:
                qs = qs.filter(is_read=True)
            elif is_read.lower() in {"false", "0", "no"}:
                qs = qs.filter(is_read=False)
        return qs


class NotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk: int):
        notif = mark_as_read(notification_id=pk, user=request.user)
        if not notif:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(NotificationSerializer(notif).data)


class NotificationReadAllView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        count = mark_all_as_read(user=request.user)
        return Response({"updated": count}, status=status.HTTP_200_OK)
