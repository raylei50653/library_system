# auth_app/views.py
from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

# 黑名單資料表（啟用 token_blacklist app 後才會有）
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from .serializers import RegisterSerializer, MeSerializer

UserModel = get_user_model()


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        s = RegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        return Response(
            {
                "id": getattr(user, "pk", None),
                "email": getattr(user, "email", None),
                "display_name": getattr(user, "display_name", None),
                "is_active": getattr(user, "is_active", True),
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    使用 email + password 登入；不依賴 USERNAME_FIELD，直接用 email 查找並 check_password。
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""

        if not email or not password:
            return Response({"detail": "email 與 password 為必填"}, status=400)

        user = UserModel.objects.filter(email__iexact=email).first()
        if not user or not user.check_password(password):
            return Response({"detail": "帳號或密碼錯誤"}, status=401)

        if not getattr(user, "is_active", True):
            return Response({"detail": "帳號未啟用"}, status=403)

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "token_type": "bearer",
            },
            status=200,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = MeSerializer(request.user).data
        return Response(data, status=200)


class LogoutView(APIView):
    """
    單一登出：提供 refresh token，將其加入黑名單。
    body: { "refresh": "<REFRESH_TOKEN>" }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_str = request.data.get("refresh")
        if not refresh_str:
            return Response({"detail": "需要 refresh token"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(refresh_str)
            token.blacklist()
        except (TokenError, InvalidToken):
            # 已失效或格式錯誤一律回 205，避免洩漏 token 狀態
            return Response({"detail": "ok"}, status=status.HTTP_205_RESET_CONTENT)

        return Response({"detail": "ok"}, status=status.HTTP_205_RESET_CONTENT)


class LogoutAllView(APIView):
    """
    全部登出：需要 access token；把目前使用者所有 refresh tokens 全數拉黑。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        tokens = OutstandingToken.objects.filter(user=user)
        count = 0
        for t in tokens:
            try:
                BlacklistedToken.objects.get_or_create(token=t)
                count += 1
            except Exception:
                continue

        return Response({"detail": "ok", "blacklisted": count}, status=status.HTTP_205_RESET_CONTENT)
