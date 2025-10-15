# books/filters.py
import django_filters
from django.db.models import Q
from .models import Book

class BookFilter(django_filters.FilterSet):
    # 與前端對齊的關鍵字參數：?query=
    query = django_filters.CharFilter(method="filter_query")

    class Meta:
        model = Book
        fields = ["category", "status"]

    def filter_query(self, queryset, name, value: str):
        if not value:
            return queryset
        return queryset.filter(
            Q(title__icontains=value) |
            Q(author__icontains=value) |
            Q(category__name__icontains=value)
        )
