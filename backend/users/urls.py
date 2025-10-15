# users/urls.py
from django.urls import path
from .views import (
    MeProfileView,
    AdminUserListView, AdminUserDetailView, AdminUserUpdateView,
)

urlpatterns = [
    # 一般使用者
    path("me/profile", MeProfileView.as_view(), name="me-profile"),

    # Admin 區
    path("admin/users", AdminUserListView.as_view(), name="admin-users-list"),
    path("admin/users/<int:pk>", AdminUserDetailView.as_view(), name="admin-users-detail"),
    path("admin/users/<int:pk>/update", AdminUserUpdateView.as_view(), name="admin-users-update"),
]
