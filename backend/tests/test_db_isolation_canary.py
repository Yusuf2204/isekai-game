"""Canary tests proving pytest is isolated from the development database."""

import hashlib
from pathlib import Path

import pytest
from sqlalchemy import text

from app.core.config import settings
from app.core.database import (
    _sqlite_file_path,
    ensure_test_database,
    get_session,
    recreate_db,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_DB_PATH = BACKEND_DIR / "test_isekai.db"
DEV_DB_PATH = BACKEND_DIR / "isekai.db"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@pytest.mark.asyncio
async def test_pytest_uses_test_database() -> None:
    """The configured database must be the test database, not the dev one."""
    configured = _sqlite_file_path(settings.database_url)
    assert configured is not None
    assert configured.expanduser().resolve() == TEST_DB_PATH.resolve()
    assert configured.expanduser().resolve() != DEV_DB_PATH.resolve()


@pytest.mark.asyncio
async def test_recreate_db_works_on_test_database() -> None:
    """recreate_db must operate successfully on the test database."""
    await recreate_db()
    async with get_session() as session:
        assert await session.scalar(text("SELECT 1")) == 1
    assert TEST_DB_PATH.exists()


@pytest.mark.asyncio
async def test_recreate_db_rejects_development_database(monkeypatch) -> None:
    """recreate_db must refuse the development database before touching it."""
    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{DEV_DB_PATH}")
    with pytest.raises(RuntimeError):
        ensure_test_database()
    with pytest.raises(RuntimeError):
        await recreate_db()


@pytest.mark.asyncio
async def test_test_database_writes_do_not_touch_development_database() -> None:
    """Writing to the test database must leave the development database intact."""
    assert DEV_DB_PATH.exists()
    before = _sha256(DEV_DB_PATH)

    await recreate_db()
    async with get_session() as session:
        await session.execute(
            text("CREATE TABLE IF NOT EXISTS canary_marker (id INTEGER)")
        )
        await session.execute(text("INSERT INTO canary_marker (id) VALUES (1)"))

    assert DEV_DB_PATH.exists()
    assert _sha256(DEV_DB_PATH) == before
