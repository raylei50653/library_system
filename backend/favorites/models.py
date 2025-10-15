from django.conf import settings
from django.db import models


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    book = models.ForeignKey(
        "books.Book",
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "book")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "book"], name="idx_favorite_user_book"),
        ]

    def __str__(self) -> str:
        return f"Favorite<{self.pk}> user={self.user_id} book={self.book_id}"

