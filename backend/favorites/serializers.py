from rest_framework import serializers

from books.serializers import BookSerializer
from .models import Favorite


class FavoriteSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ["id", "book", "created_at"]
        read_only_fields = fields
