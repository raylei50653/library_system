# Test Guide

This backend now ships with a dedicated Django settings module for test runs. Key points:

- `config/settings_test.py` inherits from the main settings but forces the database to use the local file `test_db.sqlite3`.
- Password hashing switches to `MD5PasswordHasher` during tests for speed.
- `backend/pytest.ini` points `DJANGO_SETTINGS_MODULE` at `config.settings_test`, so pytest automatically loads the lightweight configuration.

## How to Run

```bash
# run entire suite
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest -p pytest_django.plugin -p pytest_randomly

# run a single test
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/pytest -p pytest_django.plugin -p pytest_randomly path/to/test::TestClass::test_case
```

> Tip: keep the `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` prefix so that unrelated global plugins on the machine do not interfere with the run.
