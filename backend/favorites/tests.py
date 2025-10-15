import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from books.models import Book
from favorites.models import Favorite


@pytest.fixture
def user(db):
    User = get_user_model()
    return User.objects.create_user(email="reader@example.com", password="Pass1234!")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def book(db):
    return Book.objects.create(
        title="Test Book",
        author="Author",
    )


def test_list_favorites_returns_book_data(auth_client, user, book):
    Favorite.objects.create(user=user, book=book)
    url = reverse("favorite-list")

    resp = auth_client.get(url)

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["book"]["id"] == book.id
    assert data[0]["book"]["title"] == book.title


def test_add_favorite_creates_record(auth_client, user, book):
    url = reverse("favorite-detail", kwargs={"book_id": book.id})

    resp = auth_client.post(url)

    assert resp.status_code == 201
    favorite = Favorite.objects.get(user=user, book=book)
    assert favorite is not None


def test_add_favorite_twice_returns_existing(auth_client, user, book):
    Favorite.objects.create(user=user, book=book)
    url = reverse("favorite-detail", kwargs={"book_id": book.id})

    resp = auth_client.post(url)

    assert resp.status_code == 200
    assert Favorite.objects.filter(user=user, book=book).count() == 1


def test_delete_favorite_is_idempotent(auth_client, user, book):
    Favorite.objects.create(user=user, book=book)
    url = reverse("favorite-detail", kwargs={"book_id": book.id})

    resp = auth_client.delete(url)
    assert resp.status_code == 204
    assert not Favorite.objects.filter(user=user, book=book).exists()

    resp = auth_client.delete(url)
    assert resp.status_code == 204
