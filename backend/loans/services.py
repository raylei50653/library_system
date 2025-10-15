from dataclasses import dataclass
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.conf import settings

from .models import Loan
from books.models import Book
from notifications.services import create_notification


class LoanError(Exception):
    pass


class NotEnoughCopies(LoanError):
    pass


class InvalidState(LoanError):
    pass


@dataclass
class LoanResult:
    loan: Loan
    created: bool


@transaction.atomic
def loan_book(*, user, book: Book, now=None) -> LoanResult:
    now = now or timezone.now()
    b = Book.objects.select_for_update().get(pk=book.pk)
    if b.available_copies <= 0:
        raise NotEnoughCopies("No copies available")

    loan = Loan.objects.create(
        user=user,
        book=b,
        type=Loan.Type.LOAN,
        status=Loan.Status.ACTIVE,
        loaned_at=now,
        due_at=now + timezone.timedelta(days=getattr(settings, "LOAN_DAYS_DEFAULT", 14)),
    )

    Book.objects.filter(pk=b.pk).update(available_copies=F("available_copies") - 1)
    b.refresh_from_db(fields=["available_copies"])

    new_status = "unavailable" if b.available_copies == 0 else "available"
    if b.status != new_status:
        Book.objects.filter(pk=b.pk).update(status=new_status)

    return LoanResult(loan=loan, created=True)


@transaction.atomic
def reserve_book(*, user, book: Book, now=None) -> LoanResult:
    now = now or timezone.now()
    reservation = Loan.objects.create(
        user=user,
        book=book,
        type=Loan.Type.RESERVATION,
        status=Loan.Status.PENDING,
    )
    return LoanResult(loan=reservation, created=True)


@transaction.atomic
def return_loan(*, loan: Loan, now=None) -> Loan:
    now = now or timezone.now()
    if loan.type != Loan.Type.LOAN or loan.status != Loan.Status.ACTIVE:
        raise InvalidState("Only active loan can be returned")

    b = Book.objects.select_for_update().get(pk=loan.book_id)

    loan.status = Loan.Status.RETURNED
    loan.returned_at = now
    loan.save(update_fields=["status", "returned_at", "updated_at"])

    # +1 可用數量
    Book.objects.filter(pk=b.pk).update(available_copies=F("available_copies") + 1)
    b.refresh_from_db(fields=["available_copies"])

    # 嘗試自動轉出預約
    next_res = (
        Loan.objects.select_for_update(skip_locked=True)
        .filter(book_id=b.pk, type=Loan.Type.RESERVATION, status=Loan.Status.PENDING)
        .order_by("created_at")
        .first()
    )
    if next_res:
        next_res.type = Loan.Type.LOAN
        next_res.status = Loan.Status.ACTIVE
        next_res.loaned_at = now
        next_res.due_at = now + timezone.timedelta(days=getattr(settings, "LOAN_DAYS_DEFAULT", 14))
        next_res.save(update_fields=["type", "status", "loaned_at", "due_at", "updated_at"])
        Book.objects.filter(pk=b.pk).update(available_copies=F("available_copies") - 1)
        b.refresh_from_db(fields=["available_copies"])

        # 通知預約者可借書
        create_notification(
            user=next_res.user,
            notif_type="reservation_available",
            message=f"您預約的《{b.title}》已可借閱。",
            loan=next_res,
        )

    new_status = "unavailable" if b.available_copies == 0 else "available"
    if b.status != new_status:
        Book.objects.filter(pk=b.pk).update(status=new_status)

    return loan


@transaction.atomic
def renew_loan(*, loan: Loan, now=None) -> Loan:
    now = now or timezone.now()
    if loan.type != Loan.Type.LOAN or loan.status != Loan.Status.ACTIVE:
        raise InvalidState("Only active loan can be renewed")

    max_times = getattr(settings, "LOAN_MAX_RENEWALS", 1)
    if loan.renew_count >= max_times:
        raise InvalidState("Renew limit reached")

    loan.renew_count += 1
    loan.due_at = (loan.due_at or now) + timezone.timedelta(days=getattr(settings, "LOAN_RENEW_DAYS", 14))
    loan.save(update_fields=["renew_count", "due_at", "updated_at"])

    create_notification(
        user=loan.user,
        notif_type="loan_due_soon",
        message=f"您的借閱《{loan.book.title}》已續借，新的到期日為 {loan.due_at:%Y-%m-%d %H:%M}。",
        loan=loan,
    )

    return loan


def notify_due_soon(days_before: int = 1) -> int:
    now = timezone.now()
    due_edge = now + timezone.timedelta(days=days_before)
    qs = Loan.objects.filter(status=Loan.Status.ACTIVE, due_at__lte=due_edge)
    count = 0
    for loan in qs.select_related("user", "book"):
        create_notification(
            user=loan.user,
            notif_type="loan_due_soon",
            message=f"《{loan.book.title}》將於 {loan.due_at:%Y-%m-%d %H:%M} 到期。",
            loan=loan,
        )
        count += 1
    return count