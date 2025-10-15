from django.contrib import admin

from .models import Favorite


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "book", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "book__title")
    raw_id_fields = ("user", "book")
