"""Tests for time system API endpoints."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import get_session, recreate_db
from app.models.enums import RaceName, BackgroundName, GenderPresentation
from app.services.world import seed_world
from app.services.character.creation import create_character


async def _setup_db():
    """Set up database with world data."""
    await recreate_db()
    async with get_session() as session:
        await seed_world(session)


@pytest_asyncio.fixture(autouse=True)
async def _prepared_database():
    """Recreate and seed the test database before each test."""
    await _setup_db()


async def _create_character_with_session():
    """Create a test character with session."""
    async with get_session() as session:
        character, game_session = await create_character(
            session=session,
            name="Test Character",
            race_name=RaceName.HUMAN,
            background_name=BackgroundName.COMMONER,
            gender_presentation=GenderPresentation.MALE,
        )
        return character, game_session


class TestTimeState:
    """Tests for time state endpoint."""

    @pytest.mark.asyncio
    async def test_get_time_state(self):
        """Test getting current time state."""
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/time/state", params={"session_token": session_token}
            )
            assert response.status_code == 200
            data = response.json()

            assert "current_day" in data
            assert "current_time_of_day" in data
            assert "time_of_day_display" in data
            assert "day_description" in data

            assert data["current_day"] == 1
            assert data["current_time_of_day"] == "morning"
            assert data["time_of_day_display"] == "Morning"
            assert len(data["day_description"]) > 0


class TestTimeAdvance:
    """Tests for advancing time."""

    @pytest.mark.asyncio
    async def test_advance_time_one_period(self):
        """Test advancing time by one period."""
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/time/advance",
                json={"periods": 1},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            assert data["previous_day"] == 1
            assert data["previous_time_of_day"] == "morning"
            assert data["new_day"] == 1
            assert data["new_time_of_day"] == "afternoon"
            assert data["periods_advanced"] == 1
            assert "message" in data

    @pytest.mark.asyncio
    async def test_advance_time_multiple_periods(self):
        """Test advancing time by multiple periods."""
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Advance 3 periods: morning -> afternoon -> evening -> night
            response = await client.post(
                "/api/time/advance",
                json={"periods": 3},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            assert data["previous_time_of_day"] == "morning"
            assert data["new_time_of_day"] == "night"
            assert data["periods_advanced"] == 3

    @pytest.mark.asyncio
    async def test_advance_time_wraps_to_next_day(self):
        """Test advancing time wraps to next day."""
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Advance 4 periods: morning -> afternoon -> evening -> night -> morning (next day)
            response = await client.post(
                "/api/time/advance",
                json={"periods": 4},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            assert data["previous_day"] == 1
            assert data["new_day"] == 2
            assert data["new_time_of_day"] == "morning"
            assert data["periods_advanced"] == 4

    @pytest.mark.asyncio
    async def test_advance_time_invalid_periods(self):
        """Test advancing time with invalid periods."""
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Test 0 periods - Pydantic validation returns 422
            response = await client.post(
                "/api/time/advance",
                json={"periods": 0},
                params={"session_token": session_token},
            )
            assert response.status_code in (400, 422)

            # Test 5 periods (max is 4) - Pydantic validation returns 422
            response = await client.post(
                "/api/time/advance",
                json={"periods": 5},
                params={"session_token": session_token},
            )
            assert response.status_code in (400, 422)


class TestTimePeriods:
    """Tests for getting all time periods info."""

    @pytest.mark.asyncio
    async def test_get_time_periods(self):
        """Test getting all time periods information."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/time/periods")
            assert response.status_code == 200
            data = response.json()

            assert "periods" in data
            assert "current_period" in data
            assert len(data["periods"]) == 4

            # Check each period has required fields
            period_names = {p["name"] for p in data["periods"]}
            assert period_names == {"morning", "afternoon", "evening", "night"}

            for period in data["periods"]:
                assert "name" in period
                assert "display_name" in period
                assert "description" in period
                assert "available_activities" in period
                assert "npc_availability_modifier" in period
                assert isinstance(period["available_activities"], list)
                assert 0 <= period["npc_availability_modifier"] <= 1


class TestTimeIntegration:
    """Integration tests for time with travel."""

    @pytest.mark.asyncio
    async def test_travel_advances_time(self):
        """Test that travel advances time."""
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Get initial time state
            response = await client.get(
                "/api/time/state", params={"session_token": session_token}
            )
            initial_time = response.json()
            assert initial_time["current_day"] == 1
            assert initial_time["current_time_of_day"] == "morning"

            # Travel to another location
            loc_response = await client.get("/api/world/locations")
            locations = loc_response.json()["locations"]
            target = next(
                (
                    loc
                    for loc in locations
                    if loc["id"] != character.starting_location_id
                ),
                None,
            )

            await client.post(
                "/api/world/travel",
                json={"target_location_id": target["id"]},
                params={"session_token": session_token},
            )

            # Check time advanced
            response = await client.get(
                "/api/time/state", params={"session_token": session_token}
            )
            new_time = response.json()
            # Time should have advanced at least 1 period
            assert new_time["current_day"] >= initial_time["current_day"]
            # If day same, time_of_day should be later
            if new_time["current_day"] == initial_time["current_day"]:
                time_order = {"morning": 0, "afternoon": 1, "evening": 2, "night": 3}
                assert (
                    time_order[new_time["current_time_of_day"]]
                    > time_order[initial_time["current_time_of_day"]]
                )
