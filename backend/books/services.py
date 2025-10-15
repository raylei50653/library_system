from dataclasses import dataclass
from django.db import transaction
from django.db.models import F
from django.core.exceptions import ValidationError
from django.apps import apps  # ✅ 加這行
from .models import Book


@dataclass
class BookResult:
    book: Book


@transaction.atomic
def set_total_copies(*, book: Book, new_total: int) -> BookResult:
    """管理員調整總冊數。會自動校正 available，並保護 active 借閱不可被擠壓成負數。"""
    if new_total < 0:
        raise ValidationError("new_total 必須 >= 0")

    b = Book.objects.select_for_update().get(pk=book.pk)

    # ✅ 改這裡：動態取得 Loan 模型
    Loan = apps.get_model("loans", "Loan")

    active_loans = Loan.objects.filter(
        book_id=b.pk, type=Loan.Type.LOAN, status=Loan.Status.ACTIVE
    ).count()

    min_avail = max(new_total - active_loans, 0)

    b.total_copies = new_total
    if b.available_copies < min_avail:
        b.available_copies = min_avail
    elif b.available_copies > new_total:
        b.available_copies = new_total

    b.save(update_fields=["total_copies", "available_copies"])
    return BookResult(book=b)


@transaction.atomic
def recalc_available_from_loans(*, book: Book) -> BookResult:
    """保險起見：以目前 ACTIVE 借閱數重算 available（診斷／修復用）。"""
    b = Book.objects.select_for_update().get(pk=book.pk)

    # ✅ 同樣改這裡
    Loan = apps.get_model("loans", "Loan")

    active_loans = Loan.objects.filter(
        book_id=b.pk, type=Loan.Type.LOAN, status=Loan.Status.ACTIVE
    ).count()
    b.available_copies = max(b.total_copies - active_loans, 0)
    b.save(update_fields=["available_copies"])
    return BookResult(book=b)
