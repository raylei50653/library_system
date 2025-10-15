from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from books.models import Book
from loans.models import Loan

from . import services
from .models import Notification

class NotificationServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="notify@example.com",
            password="StrongPass123!",
            display_name="Notify User",
        )
        self.other_user = get_user_model().objects.create_user(
            email="other@example.com",
            password="StrongPass123!",
        )

    def make_loan(self):
        book = Book.objects.create(
            title="Test Notification Book",
            author="Tester",
        )
        return Loan.objects.create(
            user=self.user,
            book=book,
            type=Loan.Type.LOAN,
            status=Loan.Status.ACTIVE,
        )

    def test_create_notification_persists_record(self):
        notification = services.create_notification(
            user=self.user,
            notif_type="loan_due_soon",
            message="Your loan is due soon.",
        )

        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.type, "loan_due_soon")
        self.assertEqual(notification.message, "Your loan is due soon.")
        self.assertFalse(notification.is_read)

    def test_create_notification_with_loan_reference(self):
        loan = self.make_loan()

        notification = services.create_notification(
            user=self.user,
            notif_type="reservation_available",
            message="Reserved book is now available.",
            loan=loan,
        )

        self.assertEqual(notification.loan, loan)

    def test_mark_as_read_updates_flag(self):
        notification = Notification.objects.create(
            user=self.user,
            type="loan_due_soon",
            message="Please return soon.",
        )

        result = services.mark_as_read(notification_id=notification.id, user=self.user)
        self.assertIsNotNone(result)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_mark_as_read_requires_owner(self):
        notification = Notification.objects.create(
            user=self.other_user,
            type="loan_due_soon",
            message="Other user notification.",
        )

        result = services.mark_as_read(notification_id=notification.id, user=self.user)
        self.assertIsNone(result)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_mark_all_as_read_returns_updated_count(self):
        Notification.objects.create(
            user=self.user,
            type="loan_due_soon",
            message="First unread.",
        )
        Notification.objects.create(
            user=self.user,
            type="reservation_available",
            message="Second unread.",
        )
        Notification.objects.create(
            user=self.user,
            type="loan_due_soon",
            message="Already read.",
            is_read=True,
        )
        other_notification = Notification.objects.create(
            user=self.other_user,
            type="loan_due_soon",
            message="Other user unread.",
        )

        updated = services.mark_all_as_read(user=self.user)

        self.assertEqual(updated, 2)
        self.assertEqual(
            Notification.objects.filter(user=self.user, is_read=True).count(),
            3,
        )
        other_notification.refresh_from_db()
        self.assertFalse(other_notification.is_read)


class NotificationAPIViewTests(APITestCase):
    def setUp(self):
        super().setUp()

        # 🔑 關鍵：確保每個測試開始前都沒有殘留通知資料
        Notification.objects.all().delete()

        self.user = get_user_model().objects.create_user(
            email="apiuser@example.com",
            password="StrongPass123!",
        )
        self.other_user = get_user_model().objects.create_user(
            email="apiother@example.com",
            password="StrongPass123!",
        )
        self.client.force_authenticate(user=self.user)  

    def test_list_requires_authentication(self):
        self.client.force_authenticate(user=None)
        url = reverse("api-notification-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_current_user_notifications(self):
        Notification.objects.create(
            user=self.user,
            type="loan_due_soon",
            message="Loan due soon.",
        )
        Notification.objects.create(
            user=self.user,
            type="reservation_available",
            message="Reservation ready.",
        )
        Notification.objects.create(
            user=self.other_user,
            type="loan_due_soon",
            message="Other user notification.",
        )

        url = reverse("api-notification-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        returned_messages = {item["message"] for item in response.data}
        self.assertEqual(
            returned_messages,
            {"Loan due soon.", "Reservation ready."},
        )

    def test_list_supports_is_read_filter(self):
        Notification.objects.create(
            user=self.user,
            type="loan_due_soon",
            message="Unread notification.",
        )
        Notification.objects.create(
            user=self.user,
            type="loan_due_soon",
            message="Already read notification.",
            is_read=True,
        )

        url = reverse("api-notification-list")
        unread_response = self.client.get(url, {"is_read": "false"})
        read_response = self.client.get(url, {"is_read": "true"})

        self.assertEqual(len(unread_response.data), 1)
        self.assertEqual(unread_response.data[0]["message"], "Unread notification.")
        self.assertEqual(len(read_response.data), 1)
        self.assertEqual(read_response.data[0]["message"], "Already read notification.")

    def test_read_endpoint_marks_notification(self):
        notification = Notification.objects.create(
            user=self.user,
            type="loan_due_soon",
            message="Tap to mark read.",
        )

        url = reverse("api-notification-read", kwargs={"pk": notification.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertTrue(response.data["is_read"])

    def test_read_endpoint_returns_404_for_other_users_notification(self):
        notification = Notification.objects.create(
            user=self.other_user,
            type="loan_due_soon",
            message="Unauthorized access.",
        )

        url = reverse("api-notification-read", kwargs={"pk": notification.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_read_all_marks_all_unread_for_current_user(self):
        Notification.objects.create(
            user=self.user,
            type="loan_due_soon",
            message="First unread.",
        )
        Notification.objects.create(
            user=self.user,
            type="reservation_available",
            message="Second unread.",
        )
        Notification.objects.create(
            user=self.user,
            type="loan_due_soon",
            message="Already read.",
            is_read=True,
        )
        Notification.objects.create(
            user=self.other_user,
            type="loan_due_soon",
            message="Other user unread.",
        )

        url = reverse("api-notification-read-all")
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["updated"], 2)
        self.assertEqual(
            Notification.objects.filter(user=self.user, is_read=True).count(),
            3,
        )
        self.assertFalse(
            Notification.objects.get(user=self.other_user).is_read
        )
