from django.conf import settings
from django.db import models


class Loan(models.Model):
    class Type(models.TextChoices):
        LOAN = "loan", "Loan"
        RESERVATION = "reservation", "Reservation"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        RETURNED = "returned", "Returned"
        OVERDUE = "overdue", "Overdue"
        CANCELED = "canceled", "Canceled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loans",
    )
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.PROTECT,
        related_name="loans",
    )

    type = models.CharField(max_length=16, choices=Type.choices, default=Type.LOAN)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)

    loaned_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)

    renew_count = models.PositiveIntegerField(default=0)
    note = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "type"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["book", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "book"],
                condition=models.Q(type="loan", status__in=["active", "pending"]),
                name="uniq_user_book_active_pending_loan",
            ),
            models.UniqueConstraint(
                fields=["user", "book"],
                condition=models.Q(type="reservation", status="pending"),
                name="uniq_user_book_pending_reservation",
            ),
        ]

    def __str__(self):
        return f"Loan<{self.pk}> {self.user_id}→{self.book_id} {self.type}/{self.status}"
