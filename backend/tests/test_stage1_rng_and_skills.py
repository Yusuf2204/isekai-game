"""Stage 1 tests: deterministic personality RNG and seed skill validation."""

import random

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import get_session, recreate_db
from app.core.exceptions import ValidationError
from app.core.rng import get_rng
from app.main import app
from app.models.enums import BackgroundName, SkillName
from app.models.world import Background
from app.services.character.creation import (
    PERSONALITY_TRAITS,
    resolve_skill_name,
    select_random_personality_trait,
)
from app.services.world.seed import (
    BACKGROUNDS_DATA,
    seed_backgrounds,
    seed_world,
    validate_background_skills,
)


def test_personality_same_seed_same_result():
    """The same session seed must always produce the same personality."""
    first = select_random_personality_trait(get_rng(12345))
    second = select_random_personality_trait(get_rng(12345))

    assert first == second


def test_personality_varies_across_seeds():
    """Different session seeds should be able to produce different traits."""
    traits = {select_random_personality_trait(get_rng(seed))[0] for seed in range(50)}

    assert len(traits) > 1


def test_personality_is_valid_trait():
    """The selected personality must come from the configured pool."""
    result = select_random_personality_trait(get_rng(7))

    assert result in PERSONALITY_TRAITS


def test_personality_independent_of_global_random(monkeypatch):
    """Personality selection must not depend on the global random module."""
    expected = select_random_personality_trait(get_rng(999))

    random.seed(1)
    first = select_random_personality_trait(get_rng(999))
    random.seed(2)
    second = select_random_personality_trait(get_rng(999))

    assert first == expected
    assert second == expected

    def fail_global_choice(*args, **kwargs):
        raise AssertionError("global random.choice must not be used")

    monkeypatch.setattr(random, "choice", fail_global_choice)
    assert select_random_personality_trait(get_rng(999)) == expected


def test_all_background_starting_skills_valid():
    """Every background seed skill must exist in the SkillName enum."""
    valid_skills = {skill.value for skill in SkillName}

    for bg_data in BACKGROUNDS_DATA:
        skills = bg_data.get("starting_skills", {})
        assert skills, f"{bg_data['name'].value} has no starting skills"
        assert set(skills) <= valid_skills, (
            f"Invalid skills for {bg_data['name'].value}: "
            f"{sorted(set(skills) - valid_skills)}"
        )


def test_orphan_uses_negotiation_not_stealth():
    """Orphan must use a valid replacement skill instead of stealth."""
    orphan = next(
        bg_data
        for bg_data in BACKGROUNDS_DATA
        if bg_data["name"] == BackgroundName.ORPHAN
    )

    assert orphan["starting_skills"] == {"survival": 2, "negotiation": 1}
    assert "stealth" not in orphan["starting_skills"]


def test_resolve_skill_name_rejects_invalid_skill():
    """Invalid seed skills must raise a descriptive ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        resolve_skill_name("stealth", BackgroundName.ORPHAN)

    assert exc_info.value.code == "VALIDATION_ERROR"
    assert exc_info.value.details["background"] == "orphan"
    assert exc_info.value.details["invalid_skill"] == "stealth"
    assert "stealth" not in exc_info.value.details["valid_skills"]


def test_validate_background_skills_rejects_invalid_data():
    """Seed-time validation must fail loudly for invalid skill data."""
    invalid_data = [
        {
            "name": BackgroundName.ORPHAN,
            "starting_skills": {"survival": 2, "stealth": 1},
        }
    ]

    with pytest.raises(ValidationError) as exc_info:
        validate_background_skills(invalid_data)

    assert exc_info.value.details["background"] == "orphan"
    assert exc_info.value.details["invalid_skills"] == ["stealth"]


@pytest.mark.asyncio
async def test_seed_backgrounds_upserts_existing_rows():
    """Re-seeding must repair an existing background row instead of skipping it."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

    async with get_session() as session:
        result = await session.execute(
            select(Background).where(Background.name == BackgroundName.ORPHAN)
        )
        orphan = result.scalar_one()
        orphan.starting_skills = {"survival": 2, "stealth": 1}

    async with get_session() as session:
        await seed_backgrounds(session)

    async with get_session() as session:
        result = await session.execute(
            select(Background).where(Background.name == BackgroundName.ORPHAN)
        )
        orphan = result.scalar_one()

    assert orphan.starting_skills == {"survival": 2, "negotiation": 1}


@pytest.mark.asyncio
async def test_create_orphan_returns_both_skills():
    """Creating an Orphan must persist both intended starting skills."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/character/create",
            json={
                "name": "Orphan Hero",
                "race_name": "human",
                "background_name": "orphan",
                "gender_presentation": "female",
            },
        )

    assert response.status_code == 201
    data = response.json()
    skills = {skill["name"]: skill["level"] for skill in data["character"]["skills"]}

    assert skills == {"survival": 2, "negotiation": 1}


@pytest.mark.asyncio
async def test_invalid_seed_skill_returns_400():
    """Invalid legacy seed data must be reported by the API as HTTP 400."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

    async with get_session() as session:
        result = await session.execute(
            select(Background).where(Background.name == BackgroundName.ORPHAN)
        )
        orphan = result.scalar_one()
        orphan.starting_skills = {"survival": 2, "stealth": 1}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/character/create",
            json={
                "name": "Invalid Orphan",
                "race_name": "human",
                "background_name": "orphan",
                "gender_presentation": "male",
            },
        )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "VALIDATION_ERROR"
    assert detail["details"]["invalid_skill"] == "stealth"


@pytest.mark.asyncio
async def test_api_creation_deterministic_with_fixed_seed(monkeypatch):
    """Two creations with the same session seed must share a personality."""
    monkeypatch.setattr(
        "app.services.character.creation.generate_rng_seed",
        lambda: 424242,
    )

    async def create_once() -> str:
        await recreate_db()
        async with get_session() as session:
            await seed_world(session)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/character/create",
                json={
                    "name": "Deterministic Hero",
                    "race_name": "human",
                    "background_name": "commoner",
                    "gender_presentation": "male",
                },
            )

        assert response.status_code == 201
        return response.json()["character"]["personality_trait"]

    first = await create_once()
    second = await create_once()
    expected = select_random_personality_trait(get_rng(424242))[0]

    assert first == second == expected
