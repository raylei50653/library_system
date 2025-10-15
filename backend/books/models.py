# books/models.py
from django.db import models
from django.db.models import Q, F


class Category(models.Model):
    """書籍分類"""
    name = models.CharField(max_length=100, unique=True)
    # 系統分類（如「未分類」）可用來保護不被刪改，先保留欄位以備用
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Book(models.Model):
    """書籍主檔"""
    STATUS_CHOICES = [
        ("available", "Available"),
        ("maintenance", "Maintenance"),
        ("unavailable", "Unavailable"),
    ]

    title = models.CharField(max_length=255, db_index=True)
    author = models.CharField(max_length=255, db_index=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name="books",
        null=True,
        blank=True,
    )

    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="available",
        db_index=True,
    )

    # 可選：若序列化器或管理後台要顯示建立/更新時間
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        constraints = [
            # available_copies 不可大於 total_copies
            models.CheckConstraint(
                condition=Q(available_copies__gte=0),
                name="books_available_lte_total",
            ),
        ]

    def __str__(self):
        return f"{self.title} - {self.author}"
