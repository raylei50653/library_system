from django.urls import path

from .views import FavoriteDetailView, FavoriteListView


urlpatterns = [
    path("me/favorites/", FavoriteListView.as_view(), name="favorite-list"),
    path("me/favorites/<int:book_id>/", FavoriteDetailView.as_view(), name="favorite-detail"),
]
