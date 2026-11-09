"""Database configuration and session management."""

from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.models.base import Base
import app.models  # noqa: F401 - ensures all models are imported and registered


# Create async engine
# SQLite with aiosqlite doesn't support pool_size/max_overflow
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Initialize database tables."""
    # Import models here to ensure they are registered with Base.metadata
    # even if the top-level import was skipped
    from app.models import (  # noqa: F401
        GameSession,
        Character,
        CharacterAttribute,
        CharacterSkill,
        InventoryItem,
        NPC,
        NPCRelationship,
        LifeRecord,
        CharacterLegacy,
        GameplayState,
        Kingdom,
        Region,
        Location,
        Race,
        Background,
        Enemy,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


_TEST_DATABASE_PATH = Path(__file__).resolve().parents[2] / "test_isekai.db"


def _sqlite_file_path(database_url: str) -> Path | None:
    """Return the file path for a file-based SQLite URL, or None otherwise."""
    prefix = "sqlite+aiosqlite:///"
    if not database_url.startswith(prefix):
        return None
    raw_path = database_url[len(prefix) :]
    if not raw_path or raw_path == ":memory:":
        return None
    return Path(raw_path)


def ensure_test_database() -> None:
    """Raise unless the configured database is the dedicated test database."""
    db_path = _sqlite_file_path(settings.database_url)
    expected_path = _TEST_DATABASE_PATH.resolve()
    if db_path is None or db_path.expanduser().resolve() != expected_path:
        raise RuntimeError(
            "recreate_db() refused: only the test database at "
            f"{expected_path} may be recreated; "
            f"current database is {settings.database_url!r}"
        )


async def recreate_db() -> None:
    """Drop and recreate all database tables (test database only)."""
    ensure_test_database()
    from app.models import (  # noqa: F401
        GameSession,
        Character,
        CharacterAttribute,
        CharacterSkill,
        InventoryItem,
        NPC,
        NPCRelationship,
        LifeRecord,
        CharacterLegacy,
        GameplayState,
        Kingdom,
        Region,
        Location,
        Race,
        Background,
        Enemy,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()


@asynccontextmanager
async def get_session() -> AsyncSession:
    """Get a database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncSession:
    """FastAPI dependency for database session."""
    async with get_session() as session:
        yield session
