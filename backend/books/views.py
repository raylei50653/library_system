from django.db.models import Count, Q
from rest_framework import viewsets, status, permissions, generics
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination

from .models import Book, Category
from .serializers import BookSerializer, CategorySerializer
from .filters import BookFilter 

class DefaultPagination(PageNumberPagination):
    """確保列表回傳 count / results 結構"""
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = None
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["name", "id"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAdminUser()]
        return super().get_permissions()

    def get_queryset(self):
        return super().get_queryset().annotate(book_count=Count("books"))

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.books.exists():
            return Response(
                {"detail": "此分類仍有書籍，無法刪除。"},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.select_related("category").all()
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = BookFilter
    search_fields = ["title", "author", "category__name"]
    ordering_fields = ["id", "title", "author", "available_copies", "total_copies"]
    ordering = ["title"]
    pagination_class = DefaultPagination

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAdminUser()]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        """支援 ?query= 模糊搜尋 + category/status 篩選"""
        queryset = self.get_queryset()

        # 模糊搜尋
        query = request.query_params.get("query")
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(author__icontains=query)
                | Q(category__name__icontains=query)
            )

        # 額外篩選
        category = request.query_params.get("category")
        if category:
            queryset = queryset.filter(category_id=category)

        status_param = request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        queryset = self.filter_queryset(queryset)

        # 分頁處理
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class BookDetailView(generics.RetrieveAPIView):
    queryset = Book.objects.select_related("category").all()
    serializer_class = BookSerializer


# --- Admin 專用端點 (保留) ---
class AdminBookCreateView(generics.CreateAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminBookUpdateView(generics.UpdateAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAdminUser]


class AdminBookDeleteView(generics.DestroyAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAdminUser]
