"""Tests for character creation."""

import pytest
from sqlalchemy import select
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import recreate_db, get_session
from app.models.world import Location
from app.models.gameplay import GameSession
from app.services.world.seed import seed_world


@pytest.mark.asyncio
async def test_create_character_valid():
    """Test creating a character with valid data."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/character/create",
            json={
                "name": "Test Hero",
                "race_name": "human",
                "background_name": "commoner",
                "gender_presentation": "male",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Character created successfully"
    assert "session_token" in data
    assert "character" in data

    character = data["character"]
    assert character["name"] == "Test Hero"
    assert character["race_name"] == "human"
    assert character["background_name"] == "commoner"
    assert character["gender_presentation"] == "male"
    assert character["age"] == 18
    assert character["is_alive"] is True
    assert character["generation"] == 1
    assert character["session_id"] > 0
    assert character["max_health"] > 0
    assert character["current_health"] == character["max_health"]
    assert character["money"] == 50  # Commoner starting money

    # Check attributes exist
    assert len(character["attributes"]) == 5
    attr_names = {a["name"] for a in character["attributes"]}
    assert attr_names == {"strength", "agility", "intelligence", "vitality", "luck"}

    # Check skills exist (commoner has survival: 1, crafting: 1)
    assert len(character["skills"]) == 2
    skill_names = {s["name"] for s in character["skills"]}
    assert skill_names == {"survival", "crafting"}

    # Check inventory exists (commoner has 3 items)
    assert len(character["inventory"]) == 3


@pytest.mark.asyncio
async def test_create_character_all_races():
    """Test creating characters with all 6 races."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

    races = ["human", "elf", "beastkin", "dwarf", "dragonkin", "demonkin"]

    for race in races:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/character/create",
                json={
                    "name": f"Test {race.capitalize()}",
                    "race_name": race,
                    "background_name": "commoner",
                    "gender_presentation": "male",
                },
            )

        assert response.status_code == 201, f"Failed for race: {race}"
        data = response.json()
        assert data["character"]["race_name"] == race


@pytest.mark.asyncio
async def test_create_character_all_backgrounds():
    """Test creating characters with all 5 backgrounds."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

    backgrounds = [
        "commoner",
        "merchant_family",
        "orphan",
        "noble_descendant",
        "former_slave",
    ]

    for bg in backgrounds:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/character/create",
                json={
                    "name": f"Test {bg.replace('_', ' ').title()}",
                    "race_name": "human",
                    "background_name": bg,
                    "gender_presentation": "female",
                },
            )

        assert response.status_code == 201, f"Failed for background: {bg}"
        data = response.json()
        assert data["character"]["background_name"] == bg


@pytest.mark.asyncio
async def test_create_character_all_genders():
    """Test creating characters with all gender presentations."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

    genders = ["male", "female", "non_binary", "other"]

    for gender in genders:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/character/create",
                json={
                    "name": "Test Character",
                    "race_name": "human",
                    "background_name": "commoner",
                    "gender_presentation": gender,
                },
            )

        assert response.status_code == 201, f"Failed for gender: {gender}"
        data = response.json()
        assert data["character"]["gender_presentation"] == gender


@pytest.mark.asyncio
async def test_create_character_with_starting_location():
    """Test creating a character with a specific starting location."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

        # Get a valid location ID
        result = await session.execute(select(Location).where(Location.has_inn))
        location = result.scalars().first()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/character/create",
            json={
                "name": "Test Location Hero",
                "race_name": "human",
                "background_name": "commoner",
                "gender_presentation": "male",
                "starting_location_id": location.id,
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["character"]["starting_location_id"] == location.id


@pytest.mark.asyncio
async def test_create_character_invalid_race():
    """Test creating a character with invalid race."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/character/create",
            json={
                "name": "Test Hero",
                "race_name": "invalid_race",
                "background_name": "commoner",
                "gender_presentation": "male",
            },
        )

    assert response.status_code == 422  # Validation error from Pydantic


@pytest.mark.asyncio
async def test_create_character_invalid_background():
    """Test creating a character with invalid background."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/character/create",
            json={
                "name": "Test Hero",
                "race_name": "human",
                "background_name": "invalid_background",
                "gender_presentation": "male",
            },
        )

    assert response.status_code == 422  # Validation error from Pydantic


@pytest.mark.asyncio
async def test_create_character_empty_name():
    """Test creating a character with empty name."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/character/create",
            json={
                "name": "",
                "race_name": "human",
                "background_name": "commoner",
                "gender_presentation": "male",
            },
        )

    assert response.status_code == 422  # Validation error from Pydantic


@pytest.mark.asyncio
async def test_create_character_long_name():
    """Test creating a character with name too long."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/character/create",
            json={
                "name": "A" * 101,  # Max is 100
                "race_name": "human",
                "background_name": "commoner",
                "gender_presentation": "male",
            },
        )

    assert response.status_code == 422  # Validation error from Pydantic


@pytest.mark.asyncio
async def test_create_character_invalid_location():
    """Test creating a character with invalid location ID."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/character/create",
            json={
                "name": "Test Hero",
                "race_name": "human",
                "background_name": "commoner",
                "gender_presentation": "male",
                "starting_location_id": 99999,
            },
        )

    # Should return 404 for not found location
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["error"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_create_character_race_attributes_calculated():
    """Test that race attribute modifiers are correctly applied."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

    # Test Elf: base (str=8, agi=12, int=14, vit=8, luck=10) + mods (str=-1, agi=+1, int=+2, vit=-1) + Commoner bonus (str=+1, vit=+1)
    # Expected: str=8, agi=13, int=16, vit=8, luck=10
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/character/create",
            json={
                "name": "Elf Test",
                "race_name": "elf",
                "background_name": "commoner",
                "gender_presentation": "male",
            },
        )

    assert response.status_code == 201
    data = response.json()
    character = data["character"]

    attrs = {a["name"]: a["base_value"] for a in character["attributes"]}

    # Elf base + mods + Commoner bonus
    assert attrs["strength"] == 8  # 8 - 1 + 1
    assert attrs["agility"] == 13  # 12 + 1 + 0
    assert attrs["intelligence"] == 16  # 14 + 2 + 0
    assert attrs["vitality"] == 8  # 8 - 1 + 1
    assert attrs["luck"] == 10  # 10 + 0 + 0


@pytest.mark.asyncio
async def test_create_character_background_money():
    """Test that background starting money is correctly applied."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

    test_cases = [
        ("commoner", 50),
        ("merchant_family", 200),
        ("orphan", 10),
        ("noble_descendant", 300),
        ("former_slave", 20),
    ]

    for bg_name, expected_money in test_cases:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/character/create",
                json={
                    "name": "Test",
                    "race_name": "human",
                    "background_name": bg_name,
                    "gender_presentation": "male",
                },
            )

        assert response.status_code == 201, f"Failed for background: {bg_name}"
        data = response.json()
        assert (
            data["character"]["money"] == expected_money
        ), f"Money mismatch for {bg_name}"


@pytest.mark.asyncio
async def test_create_character_session_created():
    """Test that a new session is created with the character."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/character/create",
            json={
                "name": "Test Hero",
                "race_name": "human",
                "background_name": "commoner",
                "gender_presentation": "male",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert "session_token" in data
    assert len(data["session_token"]) > 0

    # Verify session was created in DB
    async with get_session() as session:
        result = await session.execute(
            select(GameSession).where(
                GameSession.session_token == data["session_token"]
            )
        )
        game_session = result.scalar_one()
        assert game_session.current_generation == 1
        assert game_session.total_generations == 1
        assert game_session.is_active is True


@pytest.mark.asyncio
async def test_create_character_demonkin_social_stigma():
    """Test that demonkin has correct social stigma in attributes."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/character/create",
            json={
                "name": "Demonkin Test",
                "race_name": "demonkin",
                "background_name": "commoner",
                "gender_presentation": "male",
            },
        )

    assert response.status_code == 201
    data = response.json()
    character = data["character"]

    attrs = {a["name"]: a["base_value"] for a in character["attributes"]}

    # Demonkin base (str=10, agi=12, int=13, vit=8, luck=12) + mods (str=0, agi=+1, int=+1, vit=-1, luck=+2) + Commoner bonus (str=+1, vit=+1)
    # Expected: str=11, agi=13, int=14, vit=8, luck=14
    assert attrs["strength"] == 11  # 10 + 0 + 1
    assert attrs["agility"] == 13  # 12 + 1 + 0
    assert attrs["intelligence"] == 14  # 13 + 1 + 0
    assert attrs["vitality"] == 8  # 8 - 1 + 1
    assert attrs["luck"] == 14  # 12 + 2 + 0


@pytest.mark.asyncio
async def test_create_character_health_calculation():
    """Test that health is calculated from vitality."""
    await recreate_db()

    async with get_session() as session:
        await seed_world(session)

    # Test with high vitality race (Dwarf: base 14, +2 mod = 16, Commoner +1 = 17)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/character/create",
            json={
                "name": "Dwarf Test",
                "race_name": "dwarf",
                "background_name": "commoner",
                "gender_presentation": "male",
            },
        )

    assert response.status_code == 201
    data = response.json()
    character = data["character"]

    # Dwarf base vit = 14, mod = +2, Commoner bonus = +1 => 17
    # Health = 100 + (17 * 5) = 185
    vit_attr = next(a for a in character["attributes"] if a["name"] == "vitality")
    assert vit_attr["base_value"] == 17
    assert character["max_health"] == 185
    assert character["current_health"] == 185


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
