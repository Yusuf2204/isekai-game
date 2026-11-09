"""Pytest configuration ensuring tests use an isolated database.

The development database lives at ``backend/isekai.db``. Tests must never
touch it, so this conftest points ``DATABASE_URL`` at ``backend/test_isekai.db``
before the application modules are imported.
"""

import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent
TEST_DB_PATH = BACKEND_DIR / "test_isekai.db"
DEV_DB_PATH = BACKEND_DIR / "isekai.db"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Must be set before app.core.config (and therefore app.core.database) is imported.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


def pytest_configure(config: pytest.Config) -> None:
    """Fail fast unless the dedicated test database is selected."""
    from app.core.config import settings
    from app.core.database import _sqlite_file_path

    configured_path = _sqlite_file_path(settings.database_url)
    if (
        configured_path is None
        or configured_path.expanduser().resolve() != TEST_DB_PATH.resolve()
    ):
        raise pytest.UsageError(
            "Test database isolation failed: "
            f"expected {TEST_DATABASE_URL!r}, got {settings.database_url!r}"
        )
    if TEST_DB_PATH.resolve() == DEV_DB_PATH.resolve():
        raise pytest.UsageError(
            "Test database path must differ from the development database."
        )


@pytest.fixture(scope="session", autouse=True)
def isolated_test_database() -> None:
    """Remove stale test database files before the suite runs."""
    if TEST_DB_PATH.resolve() == DEV_DB_PATH.resolve():
        raise RuntimeError("Refusing to remove the development database.")
    for suffix in ("", "-wal", "-shm"):
        stale = Path(f"{TEST_DB_PATH}{suffix}")
        if stale.exists():
            stale.unlink()
    yield
