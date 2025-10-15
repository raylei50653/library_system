# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Auth / Users（保留 namespace 無妨，測試不涉及）
    path("auth/", include("auth_app.urls")),
    path("users/", include(("users.urls", "users"),     namespace="users")),

    # API —— 關鍵：掛在 /api/ 並移除 namespace
    path("api/", include("books.urls")),
    path("api/", include("loans.urls")),
    path("api/", include("favorites.urls")),
    path("api/", include("notifications.urls")),

    # Chat / SSE —— 關鍵：移除 namespace
    path("chat/", include("chat.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
