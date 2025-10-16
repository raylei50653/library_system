import csv
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Book, Category


class BookAPITestCase(APITestCase):
    def setUp(self):
        self.category_history = Category.objects.create(name="歷史")
        self.category_scifi = Category.objects.create(name="科幻")

        self.history_book = Book.objects.create(
            title="世界歷史概論",
            author="Alice Historian",
            category=self.category_history,
            total_copies=4,
            available_copies=2,
            status="maintenance",
        )
        self.scifi_book = Book.objects.create(
            title="銀河漫遊指南",
            author="Bob SciFi",
            category=self.category_scifi,
            total_copies=3,
            available_copies=3,
            status="available",
        )

        self.list_url = reverse("book-list")

    def test_public_list_books_matches_module_contract(self):
        """
        對應 modules.md 3) Books：公開查詢端點應回傳書籍摘要欄位。
        """
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertIn("results", payload)
        self.assertGreaterEqual(payload["count"], 2)

        first_result = payload["results"][0]
        expected_keys = {"id", "title", "author", "available_copies", "status"}
        self.assertTrue(
            expected_keys.issubset(first_result.keys()),
            f"列表回應需至少包含 {expected_keys}",
        )

    def test_query_parameter_filters_books(self):
        """
        對應 modules.md：「GET /books?query=」應支援模糊搜尋 title/author。
        """
        response = self.client.get(self.list_url, {"query": "銀河"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        titles = [book["title"] for book in payload["results"]]
        self.assertEqual(
            titles,
            ["銀河漫遊指南"],
            "query 參數預期只回傳符合條件的書籍",
        )

    def test_filter_by_category_and_status(self):
        """
        對應 modules.md：查詢參數 category/status 應能篩選結果。
        """
        params = {"category": self.category_history.id, "status": "maintenance"}
        response = self.client.get(self.list_url, params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        results = payload["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], self.history_book.title)

    def test_retrieve_book_detail_includes_expected_fields(self):
        """
        對應 modules.md：「GET /books/{id}」應提供詳細欄位。
        """
        url = reverse("book-detail", args=[self.scifi_book.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        detail = response.json()
        required_fields = {
            "id",
            "title",
            "author",
            "total_copies",
            "available_copies",
            "status",
            "category",
        }
        self.assertTrue(
            required_fields.issubset(detail.keys()),
            f"書籍詳情需至少包含 {required_fields}",
        )
        self.assertIsInstance(detail["category"], dict)
        self.assertTrue(
            {"id", "name"}.issubset(detail["category"].keys()),
            "category 物件需帶出基本欄位",
        )

    def test_unauthenticated_users_cannot_create_books(self):
        """
        對應 modules.md：新增書籍需管理員權限，匿名請求應被拒。
        """
        payload = {
            "title": "未授權新增",
            "author": "Unknown",
            "total_copies": 1,
            "available_copies": 1,
            "status": "available",
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_admin_user_cannot_create_books(self):
        """
        對應 modules.md：一般使用者即便登入亦不得新增書籍。
        """
        user = get_user_model().objects.create_user(
            email="member@example.com",
            password="TestPass123!",
            role="user",
        )
        self.client.force_authenticate(user=user)

        payload = {
            "title": "一般使用者新增",
            "author": "Member Writer",
            "total_copies": 2,
            "available_copies": 2,
            "status": "available",
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_books_via_api(self):
        """
        對應 modules.md：管理員可透過 POST /admin/books 建立書籍。
        """
        admin = get_user_model().objects.create_user(
            email="admin@example.com",
            password="AdminPass123!",
            is_staff=True,
            role="admin",
        )
        self.client.force_authenticate(user=admin)

        payload = {
            "title": "管理員新增書籍",
            "author": "Admin Writer",
            "total_copies": 5,
            "available_copies": 5,
            "status": "available",
            "category_id": self.category_scifi.id,
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["title"], payload["title"])
        self.assertEqual(data["status"], payload["status"])

    def test_list_categories_includes_book_count_without_pagination(self):
        url = reverse("category-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertIsInstance(payload, list, "分類列表預期為陣列，不應分頁")
        first = payload[0]
        self.assertIn("book_count", first)
        self.assertIsInstance(first["book_count"], int)

    def test_order_books_by_id_desc(self):
        response = self.client.get(self.list_url, {"ordering": "-id"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        results = payload["results"]
        self.assertGreaterEqual(len(results), 2)
        self.assertEqual(results[0]["id"], self.scifi_book.id)


class ImportBooksCommandTests(TestCase):
    required_headers = [
        "title",
        "author",
        "category",
        "total_copies",
        "available_copies",
        "skip",
        "notes",
    ]

    def _write_csv(self, rows: list[dict[str, str]]) -> Path:
        tmp = tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", delete=False)
        with tmp:
            writer = csv.DictWriter(tmp, fieldnames=self.required_headers)
            writer.writeheader()
            writer.writerows(rows)
        path = Path(tmp.name)
        self.addCleanup(lambda: path.exists() and path.unlink())
        return path

    def test_import_creates_books_and_categories(self):
        csv_path = self._write_csv(
            [
                {
                    "title": "測試書籍",
                    "author": "測試作者",
                    "category": "測試分類",
                    "total_copies": "3",
                    "available_copies": "5",  # 會被指令調整成 3
                    "skip": "False",
                    "notes": "",
                },
                {
                    "title": "略過書籍",
                    "author": "其他作者",
                    "category": "測試分類",
                    "total_copies": "1",
                    "available_copies": "1",
                    "skip": "True",
                    "notes": "",
                },
            ]
        )

        call_command("import_books", str(csv_path))

        self.assertEqual(Book.objects.count(), 1)
        self.assertEqual(Category.objects.filter(name="測試分類").count(), 1)

        book = Book.objects.get()
        self.assertEqual(book.title, "測試書籍")
        self.assertEqual(book.author, "測試作者")
        self.assertEqual(book.total_copies, 3)
        self.assertEqual(book.available_copies, 3)
        self.assertEqual(book.status, "available")
        self.assertIsNotNone(book.category)
        self.assertEqual(book.category.name, "測試分類")

    def test_import_updates_existing_records(self):
        initial_csv = self._write_csv(
            [
                {
                    "title": "更新測試書籍",
                    "author": "測試作者",
                    "category": "原分類",
                    "total_copies": "2",
                    "available_copies": "1",
                    "skip": "False",
                    "notes": "",
                },
            ]
        )
        call_command("import_books", str(initial_csv))

        updated_csv = self._write_csv(
            [
                {
                    "title": "更新測試書籍",
                    "author": "測試作者",
                    "category": "新分類",
                    "total_copies": "6",
                    "available_copies": "4",
                    "skip": "False",
                    "notes": "",
                },
            ]
        )
        call_command("import_books", str(updated_csv))

        self.assertEqual(Book.objects.count(), 1)
        book = Book.objects.get()
        self.assertEqual(book.total_copies, 6)
        self.assertEqual(book.available_copies, 4)
        self.assertEqual(book.category.name, "新分類")
