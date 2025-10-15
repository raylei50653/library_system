from django.db import models
from django.conf import settings


class Notification(models.Model):
    """使用者通知（到期提醒、預約可取等）"""

    TYPE_CHOICES = [
        ("loan_due_soon", "借閱即將到期"),
        ("reservation_available", "預約書籍可取"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    # 來源關聯可選；大多來自 loans
    loan = models.ForeignKey(
        "loans.Loan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "created_at"]),
            models.Index(fields=["type"]),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.get_type_display()}"