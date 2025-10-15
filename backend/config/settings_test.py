"""
Test settings.

Overrides the default database configuration so pytest runs against a local
SQLite file instead of requiring the Postgres service defined in .env.
"""
from .settings import *  # noqa: F401,F403

TEST_DB_PATH = BASE_DIR / "test_db.sqlite3"  # type: ignore[name-defined]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(TEST_DB_PATH),
    },
}

# Use a faster password hasher during tests.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
