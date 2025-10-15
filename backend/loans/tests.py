from itertools import count

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from books.models import Book, Category

from . import services
from .models import Loan


class LoanServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="member@example.com",
            password="TestPass123!",
            role="user",
        )
        self.category = Category.objects.create(name="測試分類")
        self._title_seq = count(start=1000)

    def make_book(self, **overrides):
        title_suffix = next(self._title_seq)
        defaults = {
            "title": f"測試書籍 {title_suffix}",
            "author": "Tester",
            "category": self.category,
            "total_copies": 2,
            "available_copies": 2,
            "status": "available",
        }
        defaults.update(overrides)
        return Book.objects.create(**defaults)

    def test_loan_book_creates_active_loan_and_updates_inventory(self):
        book = self.make_book(total_copies=1, available_copies=1)
        now = timezone.now()

        result = services.loan_book(user=self.user, book=book, now=now)
        loan = result.loan
        book.refresh_from_db()

        self.assertTrue(result.created)
        self.assertEqual(loan.type, Loan.Type.LOAN)
        self.assertEqual(loan.status, Loan.Status.ACTIVE)
        self.assertEqual(loan.user, self.user)
        self.assertEqual(loan.book, book)
        self.assertEqual(loan.loaned_at, now)
        expected_due = now + timezone.timedelta(days=getattr(settings, "LOAN_DAYS_DEFAULT", 14))
        self.assertEqual(loan.due_at, expected_due)
        self.assertEqual(book.available_copies, 0)
        self.assertEqual(book.status, "unavailable")

    def test_loan_book_raises_when_no_copies_available(self):
        book = self.make_book(total_copies=1, available_copies=0, status="unavailable")

        with self.assertRaises(services.NotEnoughCopies):
            services.loan_book(user=self.user, book=book, now=timezone.now())

    def test_return_loan_marks_returned_and_releases_inventory(self):
        book = self.make_book(total_copies=1, available_copies=1)
        loaned_at = timezone.now()
        result = services.loan_book(user=self.user, book=book, now=loaned_at)
        loan = result.loan
        return_time = loaned_at + timezone.timedelta(days=3)

        services.return_loan(loan=loan, now=return_time)
        loan.refresh_from_db()
        book.refresh_from_db()

        self.assertEqual(loan.status, Loan.Status.RETURNED)
        self.assertEqual(loan.returned_at, return_time)
        self.assertEqual(book.available_copies, 1)
        self.assertEqual(book.status, "available")

    def test_return_loan_assigns_pending_reservation(self):
        book = self.make_book(total_copies=1, available_copies=1)
        loaned_at = timezone.now()
        active_loan = services.loan_book(user=self.user, book=book, now=loaned_at).loan
        other_user = get_user_model().objects.create_user(
            email="other@example.com",
            password="OtherPass123!",
            role="user",
        )
        reservation = Loan.objects.create(
            user=other_user,
            book=book,
            type=Loan.Type.RESERVATION,
            status=Loan.Status.PENDING,
        )

        return_time = loaned_at + timezone.timedelta(days=5)
        services.return_loan(loan=active_loan, now=return_time)
        active_loan.refresh_from_db()
        reservation.refresh_from_db()
        book.refresh_from_db()

        self.assertEqual(active_loan.status, Loan.Status.RETURNED)
        self.assertEqual(reservation.type, Loan.Type.LOAN)
        self.assertEqual(reservation.status, Loan.Status.ACTIVE)
        self.assertEqual(reservation.loaned_at, return_time)
        expected_due = return_time + timezone.timedelta(days=getattr(settings, "LOAN_DAYS_DEFAULT", 14))
        self.assertEqual(reservation.due_at, expected_due)
        self.assertEqual(book.available_copies, 0)
        self.assertEqual(book.status, "unavailable")

    def test_return_loan_rejects_invalid_state(self):
        book = self.make_book()
        invalid_loan = Loan.objects.create(
            user=self.user,
            book=book,
            type=Loan.Type.RESERVATION,
            status=Loan.Status.PENDING,
        )

        with self.assertRaises(services.InvalidState):
            services.return_loan(loan=invalid_loan, now=timezone.now())

    def test_renew_loan_extends_due_date_until_limit(self):
        book = self.make_book()
        loaned_at = timezone.now()
        loan = services.loan_book(user=self.user, book=book, now=loaned_at).loan
        first_due = loan.due_at
        renew_time = loaned_at + timezone.timedelta(days=7)

        loan = services.renew_loan(loan=loan, now=renew_time)
        loan.refresh_from_db()

        self.assertEqual(loan.renew_count, 1)
        expected_due = first_due + timezone.timedelta(days=getattr(settings, "LOAN_RENEW_DAYS", 14))
        self.assertEqual(loan.due_at, expected_due)

        with self.assertRaises(services.InvalidState):
            services.renew_loan(loan=loan, now=renew_time + timezone.timedelta(days=1))

    def test_reserve_book_creates_pending_reservation(self):
        book = self.make_book(total_copies=2, available_copies=2)
        now = timezone.now()

        result = services.reserve_book(user=self.user, book=book, now=now)
        reservation = result.loan
        book.refresh_from_db()

        self.assertTrue(result.created)
        self.assertEqual(reservation.type, Loan.Type.RESERVATION)
        self.assertEqual(reservation.status, Loan.Status.PENDING)
        self.assertEqual(reservation.user, self.user)
        self.assertEqual(reservation.book, book)
        self.assertIsNone(reservation.loaned_at)
        self.assertIsNone(reservation.due_at)
        self.assertEqual(book.available_copies, 2)
        self.assertEqual(book.status, "available")
