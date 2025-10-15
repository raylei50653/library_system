import os
from pathlib import Path

import pytest

# 測試統一改用 SQLite，避免 Postgres 需要 CREATE DATABASE 權限。
default_sqlite = Path(__file__).resolve().parent / "test_db.sqlite3"
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", f"sqlite:///{default_sqlite}")

_ERROR_LOG_PATH = Path(__file__).resolve().parent / "error.log"


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """Reset backend/error.log at the beginning of every pytest session."""
    _ERROR_LOG_PATH.write_text("", encoding="utf-8")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Append failure details to backend/error.log so test runs always capture the latest errors.
    """
    outcome = yield
    report = outcome.get_result()

    if not report.failed:
        return

    longrepr = getattr(report, "longreprtext", None)
    details = longrepr if longrepr is not None else str(report.longrepr)
    header = f"{report.nodeid} [{report.when}]"

    _ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _ERROR_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{header}\n{details}\n")
