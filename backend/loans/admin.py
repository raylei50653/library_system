from django.contrib import admin
from .models import Loan


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "book", "type", "status", "loaned_at", "due_at")
    list_filter = ("type", "status")
    search_fields = ("user__email", "book__title")
