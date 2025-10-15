from rest_framework import serializers
from .models import Book, Category


class CategorySerializer(serializers.ModelSerializer):
    book_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "book_count"]


class BookSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "category",
            "category_id",
            "total_copies",
            "available_copies",
            "status", 
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        total = attrs.get("total_copies", getattr(self.instance, "total_copies", 0))
        avail = attrs.get("available_copies", getattr(self.instance, "available_copies", 0))
        if avail is None:
            avail = 0
        if total is None:
            total = 0
        if avail < 0:
            raise serializers.ValidationError("available_copies 不可為負數")
        if total < 0:
            raise serializers.ValidationError("total_copies 不可為負數")
        if avail > total:
            raise serializers.ValidationError("available_copies 不可大於 total_copies")
        return attrs
