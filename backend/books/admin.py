from django.contrib import admin, messages
from django.db.models import Count
from .models import Book, Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "book_count")
    search_fields = ("name",)
    actions = ["delete_empty_categories"]

    def get_queryset(self, request):
        # 預先計算每個分類下的書籍數量
        qs = super().get_queryset(request)
        return qs.annotate(_book_count=Count("books"))

    def book_count(self, obj):
        # 顯示在後台列表
        return obj._book_count
    book_count.short_description = "掛書數"

    @admin.action(description="刪除沒有掛書的分類")
    def delete_empty_categories(self, request, queryset):
        # 批次刪除「沒有掛書的分類」
        empty_qs = queryset.annotate(c=Count("books")).filter(c=0)
        deleted = empty_qs.count()
        empty_qs.delete()
        kept = queryset.count() - deleted
        if deleted:
            self.message_user(request, f"已刪除 {deleted} 個空分類。", level=messages.SUCCESS)
        if kept:
            self.message_user(request, f"{kept} 個分類仍有書籍，已保留。", level=messages.WARNING)

    # （可選）移除預設硬刪除，避免誤刪有書的分類
    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "author",
        "category",
        "total_copies",
        "available_copies",
    )
    list_filter = ("category",)
    search_fields = ("title", "author")
