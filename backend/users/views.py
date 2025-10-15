# users/views.py
from django.contrib.auth import get_user_model
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    UserDetailSerializer, UserUpdateSerializer,
    AdminUserSerializer, AdminUserUpdateSerializer
)
from .permissions import IsAdminRole

User = get_user_model()

# ===== 我自己：/me/profile 讀寫 =====

class MeProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ser = UserDetailSerializer(request.user)
        return Response(ser.data)

    def patch(self, request):
        ser = UserUpdateSerializer(instance=request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(UserDetailSerializer(request.user).data)

# ===== Admin：/admin/users… =====

class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminRole]
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        qs = User.objects.all().order_by("id")
        email = self.request.query_params.get("email")
        active = self.request.query_params.get("active")
        role = self.request.query_params.get("role")
        if email:
            qs = qs.filter(email__icontains=email)
        if role:
            qs = qs.filter(role=role)
        if active in ("true", "false"):
            qs = qs.filter(is_active=(active == "true"))
        return qs

class AdminUserDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsAdminRole]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all()

class AdminUserUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, IsAdminRole]
    serializer_class = AdminUserUpdateSerializer
    queryset = User.objects.all()
    http_method_names = ["patch"]  # 僅允許 PATCH
