"""Stage 3 regression tests for the authoritative time engine."""

import re
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import get_session, recreate_db
from app.main import app
from app.models.enums import BackgroundName, GenderPresentation, RaceName, TimeOfDay
from app.models.gameplay import Character, GameplayState
from app.models.world import Location
from app.services.character.conditions import add_condition
from app.services.character.creation import create_character
from app.services.world import seed_world

BACKEND_DIR = Path(__file__).resolve().parent.parent
ADVANCE_TIME_PATTERN = re.compile(r"^async def advance_time\(", re.MULTILINE)


@pytest_asyncio.fixture
async def prepared_database() -> None:
    """Recreate and seed the test database for a time-authority test."""
    await recreate_db()
    async with get_session() as session:
        await seed_world(session)


async def _create_character() -> tuple[int, int, str, int | None]:
    async with get_session() as session:
        character, game_session = await create_character(
            session=session,
            name="Time Test Hero",
            race_name=RaceName.HUMAN,
            background_name=BackgroundName.COMMONER,
            gender_presentation=GenderPresentation.MALE,
        )
        return (
            character.id,
            game_session.id,
            game_session.session_token,
            character.starting_location_id,
        )


async def _set_night_with_condition(character_id: int, session_id: int) -> None:
    async with get_session() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        gameplay_state = await session.scalar(
            select(GameplayState).where(GameplayState.session_id == session_id)
        )
        assert gameplay_state is not None
        await add_condition(session, character, "minor_cut", duration=3)
        gameplay_state.current_day = 1
        gameplay_state.current_time_of_day = TimeOfDay.NIGHT


async def _condition_duration(character_id: int, condition_id: str) -> int | None:
    async with get_session() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        condition = (character.conditions or {}).get(condition_id)
        return None if condition is None else condition["duration"]


async def _other_location_id(current_location_id: int | None) -> int:
    async with get_session() as session:
        result = await session.execute(
            select(Location)
            .where(Location.id != current_location_id)
            .order_by(Location.id)
        )
        location = result.scalars().first()
        assert location is not None
        return location.id


def test_only_one_advance_time_implementation_exists() -> None:
    """The time engine must have exactly one implementation in app services."""
    definitions = [
        path
        for path in (BACKEND_DIR / "app").rglob("*.py")
        if ADVANCE_TIME_PATTERN.search(path.read_text(encoding="utf-8"))
    ]
    assert definitions == [BACKEND_DIR / "app/services/game/time.py"]


def test_callers_use_the_authoritative_time_engine() -> None:
    """Activities, travel, and the world package must not expose a second engine."""
    activities_source = (BACKEND_DIR / "app/services/game/activities.py").read_text(
        encoding="utf-8"
    )
    locations_source = (BACKEND_DIR / "app/services/world/locations.py").read_text(
        encoding="utf-8"
    )
    world_init_source = (BACKEND_DIR / "app/services/world/__init__.py").read_text(
        encoding="utf-8"
    )

    assert "world_advance_time" not in activities_source
    assert "async def advance_time(" not in locations_source
    assert "from app.services.game.time import advance_time" in locations_source
    assert "advance_time" not in world_init_source


@pytest.mark.asyncio
async def test_time_api_ticks_condition_once_when_day_changes(
    prepared_database,
) -> None:
    """The authoritative time API must tick conditions exactly once per day."""
    character_id, session_id, session_token, _ = await _create_character()
    await _set_night_with_condition(character_id, session_id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/time/advance",
            json={"periods": 1},
            params={"session_token": session_token},
        )

    assert response.status_code == 200
    assert response.json()["new_day"] == 2
    assert await _condition_duration(character_id, "minor_cut") == 2


@pytest.mark.asyncio
async def test_explore_ticks_condition_once_when_day_changes(
    prepared_database,
) -> None:
    """Explore must use the authoritative engine and tick conditions once."""
    character_id, session_id, session_token, _ = await _create_character()
    await _set_night_with_condition(character_id, session_id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/activities/explore",
            json={},
            params={"session_token": session_token},
        )

    assert response.status_code == 200
    assert response.json()["result"]["new_day"] == 2
    assert await _condition_duration(character_id, "minor_cut") == 2


@pytest.mark.asyncio
async def test_rest_ticks_condition_once_when_day_changes(
    prepared_database,
) -> None:
    """Rest must use the authoritative engine and tick conditions once."""
    character_id, session_id, session_token, _ = await _create_character()
    await _set_night_with_condition(character_id, session_id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/activities/rest",
            json={"duration": "short"},
            params={"session_token": session_token},
        )

    assert response.status_code == 200
    assert response.json()["result"]["new_day"] == 2
    assert await _condition_duration(character_id, "minor_cut") == 2


@pytest.mark.asyncio
async def test_work_ticks_condition_once_when_day_changes(
    prepared_database,
) -> None:
    """Work must use the authoritative engine and tick conditions once."""
    character_id, session_id, session_token, _ = await _create_character()
    await _set_night_with_condition(character_id, session_id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/activities/work",
            json={},
            params={"session_token": session_token},
        )

    assert response.status_code == 200
    assert response.json()["result"]["new_day"] == 2
    assert await _condition_duration(character_id, "minor_cut") == 2


@pytest.mark.asyncio
async def test_travel_ticks_condition_once_when_day_changes(
    prepared_database,
) -> None:
    """Travel must use the authoritative engine and tick conditions once."""
    character_id, session_id, session_token, location_id = await _create_character()
    target_location_id = await _other_location_id(location_id)
    await _set_night_with_condition(character_id, session_id)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/world/travel",
            json={"target_location_id": target_location_id},
            params={"session_token": session_token},
        )

    assert response.status_code == 200
    assert response.json()["new_day"] == 2
    assert await _condition_duration(character_id, "minor_cut") == 2


@pytest.mark.asyncio
async def test_activity_does_not_tick_condition_without_day_change(
    prepared_database,
) -> None:
    """A time advance that stays within the same day must not tick conditions."""
    character_id, _, session_token, _ = await _create_character()

    async with get_session() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        await add_condition(session, character, "minor_cut", duration=3)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/activities/explore",
            json={},
            params={"session_token": session_token},
        )

    assert response.status_code == 200
    assert response.json()["result"]["new_day"] == 1
    assert await _condition_duration(character_id, "minor_cut") == 3
