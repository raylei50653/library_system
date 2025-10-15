from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken


User = get_user_model()


class RegisterViewTests(APITestCase):
    def test_register_success(self):
        payload = {
            "email": "newuser@example.com",
            "password": "StrongPass123",
            "display_name": "New User",
        }

        url = reverse("auth-register")
        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["email"], payload["email"])
        self.assertEqual(response.data["display_name"], payload["display_name"])
        self.assertTrue(response.data["is_active"])
        self.assertTrue(User.objects.filter(email=payload["email"]).exists())

    def test_register_duplicate_email(self):
        User.objects.create_user(email="dup@example.com", password="StrongPass123")
        url = reverse("auth-register")
        response = self.client.post(
            url,
            {"email": "dup@example.com", "password": "StrongPass123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_weak_password(self):
        url = reverse("auth-register")
        response = self.client.post(
            url,
            {"email": "weak@example.com", "password": "123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)


class LoginViewTests(APITestCase):
    def setUp(self):
        self.password = "StrongPass123"
        self.user = User.objects.create_user(
            email="member@example.com", password=self.password, display_name="Member"
        )

    def test_login_success_returns_tokens(self):
        url = reverse("auth-login")
        response = self.client.post(
            url,
            {"email": self.user.email, "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertEqual(response.data.get("token_type"), "bearer")

    def test_login_inactive_user_blocked(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        url = reverse("auth-login")
        response = self.client.post(
            url,
            {"email": self.user.email, "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data.get("detail"), "帳號未啟用")

    def test_login_wrong_credentials(self):
        url = reverse("auth-login")
        response = self.client.post(
            url,
            {"email": self.user.email, "password": "WrongPassword"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data.get("detail"), "帳號或密碼錯誤")

    def test_login_missing_fields(self):
        url = reverse("auth-login")
        response = self.client.post(url, {"email": ""}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("detail"), "email 與 password 為必填")


class MeViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="me@example.com",
            password="StrongPass123",
            display_name="Me User",
            role="admin",
        )

    def _authenticate(self):
        access = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_me_requires_authentication(self):
        url = reverse("auth-me")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_user_profile(self):
        self._authenticate()

        url = reverse("auth-me")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["display_name"], self.user.display_name)
        self.assertEqual(response.data["role"], self.user.role)
        self.assertTrue(response.data["is_active"])


class LogoutViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="logout@example.com", password="StrongPass123"
        )

    def test_logout_invalid_without_refresh(self):
        url = reverse("auth-logout")
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data.get("detail"), "需要 refresh token")

    def test_logout_blacklists_refresh_token(self):
        refresh = RefreshToken.for_user(self.user)
        url = reverse("auth-logout")

        response = self.client.post(url, {"refresh": str(refresh)}, format="json")

        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertEqual(response.data.get("detail"), "ok")
        self.assertTrue(
            BlacklistedToken.objects.filter(token__jti=refresh["jti"]).exists()
        )

    def test_logout_with_invalid_token_no_error(self):
        url = reverse("auth-logout")
        response = self.client.post(
            url, {"refresh": "invalid-token-value"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertEqual(response.data.get("detail"), "ok")


class LogoutAllViewTests(APITestCase):
    def setUp(self):
        self.password = "StrongPass123"
        self.user = User.objects.create_user(
            email="logoutall@example.com", password=self.password
        )
        self.access = RefreshToken.for_user(self.user).access_token

    def _auth_client(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def test_logout_all_blacklists_all_tokens(self):
        # 建立額外 refresh tokens，模擬多裝置登入
        refresh_tokens = [RefreshToken.for_user(self.user) for _ in range(2)]

        self.assertEqual(
            OutstandingToken.objects.filter(user=self.user).count(), len(refresh_tokens) + 1
        )

        self._auth_client()
        url = reverse("auth-logout-all")
        response = self.client.post(url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertEqual(response.data.get("detail"), "ok")
        self.assertEqual(
            response.data.get("blacklisted"), 
            OutstandingToken.objects.filter(user=self.user).count()
        )
        self.assertEqual(
            BlacklistedToken.objects.filter(token__user=self.user).count(),
            OutstandingToken.objects.filter(user=self.user).count(),
        )
