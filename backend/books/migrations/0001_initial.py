# Combined migration created by Codex to reflect the current models state.
import django.db.models.deletion
from django.db import migrations, models


def seed_uncategorized_category(apps, schema_editor):
    Category = apps.get_model("books", "Category")
    Book = apps.get_model("books", "Book")

    uncategorized, created = Category.objects.get_or_create(
        name="未分類",
        defaults={"is_system": True},
    )

    if not created and not uncategorized.is_system:
        uncategorized.is_system = True
        uncategorized.save(update_fields=["is_system"])

    Book.objects.filter(category__isnull=True).update(category=uncategorized)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("is_system", models.BooleanField(default=False)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Book",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("isbn", models.CharField(max_length=20, unique=True)),
                ("title", models.CharField(max_length=255)),
                ("author", models.CharField(max_length=255)),
                ("total_copies", models.PositiveIntegerField(default=1)),
                ("available_copies", models.PositiveIntegerField(default=1)),
                ("status", models.CharField(default="available", max_length=20)),
                ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="books", to="books.category")),
            ],
            options={
                "ordering": ["title"],
            },
        ),
        migrations.RunPython(seed_uncategorized_category, noop),
    ]
