import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from books.models import Book, Category


@dataclass(frozen=True)
class ImportStats:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    categories_created: int = 0


class Command(BaseCommand):
    help = "Import book records from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            nargs="?",
            help="Path to the CSV file. Defaults to 'books_seed.csv' inside the backend directory.",
        )

    def handle(self, *args, **options):
        csv_path = options.get("csv_path")
        path = self._resolve_path(csv_path)

        if not path.exists():
            raise CommandError(f"CSV 檔案不存在：{path}")

        self.stdout.write(f"開始匯入書籍資料：{path}")

        with transaction.atomic():
            stats, warnings = self._import_from_csv(path)
            if warnings:
                self.stdout.write(self.style.WARNING("注意："))
                for message in warnings:
                    self.stdout.write(f"  - {message}")

            summary = (
                f"完成匯入：新增 {stats.created} 筆、更新 {stats.updated} 筆、"
                f"略過 {stats.skipped} 筆、產生 {stats.categories_created} 個新分類。"
            )
            self.stdout.write(self.style.SUCCESS(summary))

    def _resolve_path(self, user_path: Optional[str]) -> Path:
        base_dir = Path(settings.BASE_DIR)
        if not user_path:
            return base_dir / "books_seed.csv"

        candidate = Path(user_path)
        if candidate.is_absolute():
            return candidate
        return (base_dir / candidate).resolve()

    def _import_from_csv(self, path: Path) -> tuple[ImportStats, list[str]]:
        created = 0
        updated = 0
        skipped = 0
        categories_created = 0
        warnings: list[str] = []

        with path.open("r", encoding="utf-8-sig", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            required_columns = {
                "title",
                "author",
                "category",
                "total_copies",
                "available_copies",
                "skip",
            }
            if reader.fieldnames is None:
                raise CommandError("CSV 檔案沒有標題列。")

            missing = required_columns - set(name.strip() for name in reader.fieldnames)
            if missing:
                raise CommandError(f"CSV 缺少必要欄位：{', '.join(sorted(missing))}")

            category_cache: dict[str, Category] = {}
            valid_status = {choice[0] for choice in Book.STATUS_CHOICES}
            default_status = Book._meta.get_field("status").default

            for row_index, row in enumerate(reader, start=2):  # Header 為第 1 行
                if self._should_skip(row.get("skip")):
                    skipped += 1
                    continue

                title = (row.get("title") or "").strip()
                author = (row.get("author") or "").strip()
                if not title or not author:
                    raise CommandError(
                        f"第 {row_index} 行缺少必要欄位（title/author）。"
                    )

                category_name = (row.get("category") or "").strip()
                if category_name:
                    category = category_cache.get(category_name)
                    if category is None:
                        category, created_flag = Category.objects.get_or_create(
                            name=category_name
                        )
                        category_cache[category_name] = category
                        if created_flag:
                            categories_created += 1
                else:
                    category = None

                total_copies = self._safe_int(
                    row.get("total_copies"), default=1, row_index=row_index, field="total_copies"
                )
                available_copies = self._safe_int(
                    row.get("available_copies"),
                    default=total_copies,
                    row_index=row_index,
                    field="available_copies",
                )

                if available_copies > total_copies:
                    warnings.append(
                        f"第 {row_index} 行 available_copies ({available_copies}) "
                        f"超過 total_copies ({total_copies})，已自動調整。"
                    )
                    available_copies = total_copies
                if available_copies < 0:
                    warnings.append(
                        f"第 {row_index} 行 available_copies ({available_copies}) "
                        "為負值，已調整為 0。"
                    )
                    available_copies = 0
                if total_copies < 0:
                    warnings.append(
                        f"第 {row_index} 行 total_copies ({total_copies}) 為負值，已調整為 0。"
                    )
                    total_copies = 0

                status_value = (row.get("status") or default_status or "").strip() or default_status
                if status_value not in valid_status:
                    raise CommandError(
                        f"第 {row_index} 行的 status 值無效：{status_value}。"
                    )

                book, created_flag = Book.objects.update_or_create(
                    title=title,
                    author=author,
                    defaults={
                        "category": category,
                        "total_copies": total_copies,
                        "available_copies": available_copies,
                        "status": status_value,
                    },
                )

                if created_flag:
                    created += 1
                else:
                    updated += 1

        return ImportStats(
            created=created,
            updated=updated,
            skipped=skipped,
            categories_created=categories_created,
        ), warnings

    def _should_skip(self, raw_value: Optional[str]) -> bool:
        if raw_value is None:
            return False
        value = str(raw_value).strip().lower()
        return value in {"1", "true", "yes", "y"}

    def _safe_int(
        self,
        raw_value: Optional[str],
        *,
        default: int,
        row_index: int,
        field: str,
    ) -> int:
        if raw_value is None or str(raw_value).strip() == "":
            return default
        try:
            return int(float(str(raw_value).strip()))
        except ValueError as exc:  # pragma: no cover - defensive
            raise CommandError(
                f"第 {row_index} 行欄位 {field} 的值無法轉換為整數：{raw_value}"
            ) from exc

