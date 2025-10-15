from rest_framework import serializers
from .models import Loan
from . import services
from books.models import Book

class LoanListSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)


    class Meta:
        model = Loan
        fields = [
            "id", "type", "status", "book", "book_title",
            "loaned_at", "due_at", "returned_at", "renew_count",
            "created_at",
        ]
        read_only_fields = fields

class LoanCreateSerializer(serializers.Serializer):
    book_id = serializers.IntegerField()


    def validate(self, data):
        try:
            data["book"] = Book.objects.get(pk=data["book_id"])
        except Book.DoesNotExist:
            raise serializers.ValidationError("Book not found")
        return data


    def create(self, validated_data):
        user = self.context["request"].user
        res = services.loan_book(user=user, book=validated_data["book"])
        return res.loan

class ReservationCreateSerializer(serializers.Serializer):
    book_id = serializers.IntegerField()


    def validate(self, data):
        try:
            data["book"] = Book.objects.get(pk=data["book_id"])
        except Book.DoesNotExist:
            raise serializers.ValidationError("Book not found")
        return data


    def create(self, validated_data):
        user = self.context["request"].user
        res = services.reserve_book(user=user, book=validated_data["book"])
        return res.loan

class LoanActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = ["id", "status", "due_at", "returned_at", "renew_count"]
        read_only_fields = fields

class AdminLoanPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = ["status", "note"]