from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from books.models import Book
from .models import Favorite
from .serializers import FavoriteSerializer


class FavoriteListView(generics.ListAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Favorite.objects.filter(user=self.request.user)
            .select_related("book", "book__category")
            .order_by("-created_at")
        )

    def list(self, request, *args, **kwargs):
        """Override to disable pagination and return plain list."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)  # 👈 不再使用 paginator

class FavoriteDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, book_id: int):
        book = get_object_or_404(Book, pk=book_id)
        favorite, created = Favorite.objects.get_or_create(user=request.user, book=book)
        serializer = FavoriteSerializer(favorite, context={"request": request})
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code)

    def delete(self, request, book_id: int):
        Favorite.objects.filter(user=request.user, book_id=book_id).delete()
        # Idempotent delete: even if it did not exist, return 204.
        return Response(status=status.HTTP_204_NO_CONTENT)
