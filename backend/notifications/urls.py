from django.urls import path
from . import views

urlpatterns = [
    # /api/me/notifications/...
    path("me/notifications/", views.NotificationListView.as_view(), name="api-notification-list"),
    path("me/notifications/<int:pk>/read/", views.NotificationReadView.as_view(), name="api-notification-read"),
    path("me/notifications/read-all/", views.NotificationReadAllView.as_view(), name="api-notification-read-all"),
]
