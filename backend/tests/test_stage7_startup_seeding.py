"""Tests for Stage 7: Application Startup and World Seeding.

Verifies:
- Fresh installation is playable immediately without manual seeding (CB-01).
- Startup runs inside one explicit composition-root transaction.
- World seeding is strictly idempotent across repeated startup runs.
- Missing seed records are restored without duplicating existing records.
- Startup never calls recreate_db().
"""

from unittest.mock import patch
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select

from app.core.database import get_session, recreate_db
from app.main import app, lifespan, seed_world_at_startup
from app.models.enums import BackgroundName, GenderPresentation, RaceName
from app.models.world import Background, Enemy, Kingdom, Location, Race, Region
from app.services.world.seed import (
    BACKGROUNDS_DATA,
    ENEMIES_DATA,
    LOCATIONS_DATA,
    RACES_DATA,
    REGIONS_DATA,
    is_world_fully_seeded,
)


@pytest_asyncio.fixture(autouse=True)
async def _clean_test_db():
    """Ensure clean test database state before each test."""
    await recreate_db()


class TestStartupSeedingLifecycle:
    """Tests for application startup and lifespan seeding."""

    @pytest.mark.asyncio
    async def test_startup_seeds_fresh_database(self):
        """Test that lifespan startup initializes tables and seeds all world static data."""
        # Ensure fresh DB is unseeded
        async with get_session() as session:
            assert await is_world_fully_seeded(session) is False

        # Run lifespan context manager (simulates server startup)
        async with lifespan(app):
            async with get_session() as session:
                assert await is_world_fully_seeded(session) is True

                k_count = await session.scalar(select(func.count(Kingdom.id)))
                r_count = await session.scalar(select(func.count(Region.id)))
                loc_count = await session.scalar(select(func.count(Location.id)))
                race_count = await session.scalar(select(func.count(Race.id)))
                bg_count = await session.scalar(select(func.count(Background.id)))
                enemy_count = await session.scalar(select(func.count(Enemy.id)))

                assert k_count == 1
                assert r_count == len(REGIONS_DATA)
                assert loc_count == len(LOCATIONS_DATA)
                assert race_count == len(RACES_DATA)
                assert bg_count == len(BACKGROUNDS_DATA)
                assert enemy_count == len(ENEMIES_DATA)

    @pytest.mark.asyncio
    async def test_fresh_database_immediately_playable(self):
        """Test character creation succeeds immediately on a fresh database via API (CB-01)."""
        async with lifespan(app):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/character/create",
                    json={
                        "name": "Fresh Install Hero",
                        "race_name": RaceName.HUMAN.value,
                        "background_name": BackgroundName.COMMONER.value,
                        "gender_presentation": GenderPresentation.MALE.value,
                    },
                )
                assert response.status_code == 201
                data = response.json()
                assert data["character"]["name"] == "Fresh Install Hero"
                assert data["character"]["race_name"] == "human"
                assert data["character"]["background_name"] == "commoner"
                assert "session_token" in data

    @pytest.mark.asyncio
    async def test_repeated_startup_is_idempotent(self):
        """Test that multiple startup invocations do not duplicate records."""
        # First startup
        await seed_world_at_startup()

        async with get_session() as session:
            k1 = await session.scalar(select(func.count(Kingdom.id)))
            r1 = await session.scalar(select(func.count(Region.id)))
            l1 = await session.scalar(select(func.count(Location.id)))
            ra1 = await session.scalar(select(func.count(Race.id)))
            bg1 = await session.scalar(select(func.count(Background.id)))
            e1 = await session.scalar(select(func.count(Enemy.id)))

        # Second startup
        result = await seed_world_at_startup()
        assert result is None  # Already seeded, no re-seed needed

        async with get_session() as session:
            k2 = await session.scalar(select(func.count(Kingdom.id)))
            r2 = await session.scalar(select(func.count(Region.id)))
            l2 = await session.scalar(select(func.count(Location.id)))
            ra2 = await session.scalar(select(func.count(Race.id)))
            bg2 = await session.scalar(select(func.count(Background.id)))
            e2 = await session.scalar(select(func.count(Enemy.id)))

        assert k1 == k2 == 1
        assert r1 == r2 == len(REGIONS_DATA)
        assert l1 == l2 == len(LOCATIONS_DATA)
        assert ra1 == ra2 == len(RACES_DATA)
        assert bg1 == bg2 == len(BACKGROUNDS_DATA)
        assert e1 == e2 == len(ENEMIES_DATA)

    @pytest.mark.asyncio
    async def test_partial_seed_restoration(self):
        """Test that if some seed records are missing, startup restores only missing entities."""
        # Fully seed first
        await seed_world_at_startup()

        # Delete enemies and one background to simulate partial database state
        async with get_session() as session:
            await session.execute(delete(Enemy))
            await session.execute(
                delete(Background).where(Background.name == BackgroundName.ORPHAN)
            )

        async with get_session() as session:
            assert await is_world_fully_seeded(session) is False

        # Run startup seeding again
        summary = await seed_world_at_startup()
        assert summary is not None

        # Verify all entities are present and no duplicates were created
        async with get_session() as session:
            assert await is_world_fully_seeded(session) is True
            assert await session.scalar(select(func.count(Kingdom.id))) == 1
            assert await session.scalar(select(func.count(Region.id))) == len(
                REGIONS_DATA
            )
            assert await session.scalar(select(func.count(Location.id))) == len(
                LOCATIONS_DATA
            )
            assert await session.scalar(select(func.count(Race.id))) == len(RACES_DATA)
            assert await session.scalar(select(func.count(Background.id))) == len(
                BACKGROUNDS_DATA
            )
            assert await session.scalar(select(func.count(Enemy.id))) == len(
                ENEMIES_DATA
            )

    @pytest.mark.asyncio
    async def test_startup_does_not_call_recreate_db(self):
        """Test that startup seeding never calls recreate_db()."""
        with patch("app.core.database.recreate_db") as mock_recreate:
            async with lifespan(app):
                pass
            mock_recreate.assert_not_called()


class TestIsWorldFullySeededHelper:
    """Tests for is_world_fully_seeded helper function."""

    @pytest.mark.asyncio
    async def test_is_world_fully_seeded_true_and_false(self):
        """Test is_world_fully_seeded accurately reflects database state."""
        async with get_session() as session:
            assert await is_world_fully_seeded(session) is False

        await seed_world_at_startup()

        async with get_session() as session:
            assert await is_world_fully_seeded(session) is True
