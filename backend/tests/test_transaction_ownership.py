"""Regression tests for caller-owned transaction boundaries."""

from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.database import get_session, recreate_db
from app.models.enums import BackgroundName, GenderPresentation, RaceName
from app.models.gameplay import (
    Character,
    CharacterAttribute,
    CharacterSkill,
    GameSession,
    GameplayState,
    InventoryItem,
)
from app.models.world import Kingdom, Location, Region
from app.services.character.creation import create_character
from app.services.world.seed import seed_world

BACKEND_DIR = Path(__file__).resolve().parent.parent
COMMIT_FREE_FILES = (
    "app/api/inventory.py",
    "app/api/time.py",
    "app/services/character/creation.py",
    "app/services/game/activities.py",
    "app/services/world/locations.py",
    "app/services/world/seed.py",
)


async def _count(session, model) -> int:
    return await session.scalar(select(func.count(model.id))) or 0


async def _create_test_character(session):
    return await create_character(
        session=session,
        name="Transaction Hero",
        race_name=RaceName.HUMAN,
        background_name=BackgroundName.COMMONER,
        gender_presentation=GenderPresentation.MALE,
    )


@pytest.mark.asyncio
async def test_character_creation_persists_all_tables_at_caller_commit() -> None:
    """Character creation must persist all related rows when the caller commits."""
    await recreate_db()
    async with get_session() as session:
        await seed_world(session)

    async with get_session() as session:
        character, game_session = await _create_test_character(session)
        character_id = character.id
        game_session_id = game_session.id

    async with get_session() as session:
        character = await session.get(Character, character_id)
        assert character is not None
        assert character.name == "Transaction Hero"
        assert (
            await session.scalar(
                select(func.count(CharacterAttribute.id)).where(
                    CharacterAttribute.character_id == character_id
                )
            )
            == 5
        )
        assert (
            await session.scalar(
                select(func.count(CharacterSkill.id)).where(
                    CharacterSkill.character_id == character_id
                )
            )
            > 0
        )
        assert (
            await session.scalar(
                select(func.count(InventoryItem.id)).where(
                    InventoryItem.character_id == character_id
                )
            )
            > 0
        )
        assert (
            await session.scalar(
                select(func.count(GameplayState.id)).where(
                    GameplayState.session_id == game_session_id
                )
            )
            == 1
        )


@pytest.mark.asyncio
async def test_failed_request_rolls_back_all_character_writes() -> None:
    """A failure after multi-table writes must not leave partial character data."""
    await recreate_db()
    async with get_session() as session:
        await seed_world(session)

    with pytest.raises(RuntimeError, match="abort"):
        async with get_session() as session:
            await _create_test_character(session)
            raise RuntimeError("abort")

    async with get_session() as session:
        assert await _count(session, Character) == 0
        assert await _count(session, GameSession) == 0
        assert await _count(session, CharacterAttribute) == 0
        assert await _count(session, CharacterSkill) == 0
        assert await _count(session, InventoryItem) == 0
        assert await _count(session, GameplayState) == 0
        assert await _count(session, Kingdom) == 1


@pytest.mark.asyncio
async def test_seed_world_does_not_commit_before_caller_finishes() -> None:
    """World seeding must remain uncommitted until the composition root commits."""
    await recreate_db()

    with pytest.raises(RuntimeError, match="abort"):
        async with get_session() as session:
            await seed_world(session)
            raise RuntimeError("abort")

    async with get_session() as session:
        assert await _count(session, Kingdom) == 0
        assert await _count(session, Region) == 0
        assert await _count(session, Location) == 0


def test_services_and_endpoints_do_not_call_commit() -> None:
    """Commit calls must remain at the request/context-manager boundary only."""
    for relative_path in COMMIT_FREE_FILES:
        source = (BACKEND_DIR / relative_path).read_text(encoding="utf-8")
        assert "session.commit()" not in source, relative_path
