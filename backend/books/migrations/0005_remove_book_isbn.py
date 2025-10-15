from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("books", "0004_alter_book_isbn"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="book",
            name="isbn",
        ),
    ]
