"""Tests for unified progression status and cross-system integration."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.core.database import get_session, recreate_db
from app.models.enums import (
    RaceName,
    BackgroundName,
    GenderPresentation,
    SkillName,
    AttributeName,
)
from app.models.gameplay import Character, CharacterSkill, CharacterAttribute
from app.services.world import seed_world
from app.services.character.creation import create_character
from app.services.character.progression import (
    grant_character_xp,
    grant_skill_xp,
    allocate_attribute_points,
    get_unified_progression_status,
)


async def _setup_db():
    """Set up database with world data."""
    await recreate_db()
    async with get_session() as session:
        await seed_world(session)
        return session


async def _create_character_with_session(
    background: BackgroundName = BackgroundName.COMMONER,
):
    """Create a test character with session."""
    async with get_session() as session:
        character, game_session = await create_character(
            session=session,
            name="Test Character",
            race_name=RaceName.HUMAN,
            background_name=background,
            gender_presentation=GenderPresentation.MALE,
        )
        return character, game_session


async def _get_character_in_session(session, character_id: int) -> Character:
    """Get character in a specific session."""
    result = await session.execute(
        select(Character).where(Character.id == character_id)
    )
    return result.scalar_one()


async def _get_skill_in_session(
    session, character_id: int, skill_name: SkillName
) -> CharacterSkill | None:
    """Get skill in a specific session."""
    result = await session.execute(
        select(CharacterSkill).where(
            CharacterSkill.character_id == character_id,
            CharacterSkill.name == skill_name,
        )
    )
    return result.scalar_one_or_none()


async def _get_attribute_in_session(
    session, character_id: int, attr_name: AttributeName
) -> CharacterAttribute | None:
    """Get attribute in a specific session."""
    result = await session.execute(
        select(CharacterAttribute).where(
            CharacterAttribute.character_id == character_id,
            CharacterAttribute.name == attr_name,
        )
    )
    return result.scalar_one_or_none()


class TestUnifiedProgressionStatus:
    """Tests for unified progression status service and endpoint."""

    @pytest.mark.asyncio
    async def test_get_unified_progression_status_service(self):
        """Test the get_unified_progression_status service function."""
        await _setup_db()
        character, game_session = await _create_character_with_session(
            BackgroundName.MERCHANT_FAMILY
        )

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            result = await get_unified_progression_status(session, character)

            # Check structure
            assert "character" in result
            assert "skills" in result
            assert "attributes" in result

            # Check character progression
            char_prog = result["character"]
            assert char_prog["level"] == 1
            assert char_prog["experience"] == 0
            assert char_prog["experience_for_next_level"] == 150  # 1 * 100 + 50
            assert char_prog["progress_percent"] == 0.0
            assert char_prog["attribute_points"] == 0

            # Check skills (MERCHANT_FAMILY starts with trading:2, negotiation:1)
            skills = result["skills"]
            skill_names = [s["name"] for s in skills]
            assert "trading" in skill_names
            assert "negotiation" in skill_names

            trading = next(s for s in skills if s["name"] == "trading")
            assert trading["level"] == 2
            assert trading["experience"] == 0
            assert trading["experience_for_next_level"] == 250  # 2 * 100 + 50

            negotiation = next(s for s in skills if s["name"] == "negotiation")
            assert negotiation["level"] == 1
            assert negotiation["experience"] == 0
            assert negotiation["experience_for_next_level"] == 150  # 1 * 100 + 50

            # Check attributes
            attributes = result["attributes"]
            attr_names = [a["name"] for a in attributes]
            assert "strength" in attr_names
            assert "agility" in attr_names
            assert "intelligence" in attr_names
            assert "vitality" in attr_names
            assert "luck" in attr_names

            for attr in attributes:
                assert "name" in attr
                assert "base_value" in attr
                assert "current_value" in attr
                assert "experience" in attr
                assert attr["current_value"] >= attr["base_value"]

    @pytest.mark.asyncio
    async def test_unified_progression_endpoint(self):
        """Test the unified progression API endpoint."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/character/progression",
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            # Check structure
            assert "character" in data
            assert "skills" in data
            assert "attributes" in data

            # Check character progression
            char = data["character"]
            assert char["level"] == 1
            assert char["experience"] == 0
            assert char["experience_for_next_level"] == 150
            assert char["progress_percent"] == 0.0
            assert char["attribute_points"] == 0

            # Check skills (COMMONER starts with survival:1, crafting:1)
            skills = data["skills"]
            skill_names = [s["name"] for s in skills]
            assert "survival" in skill_names
            assert "crafting" in skill_names

            survival = next(s for s in skills if s["name"] == "survival")
            assert survival["level"] == 1
            assert survival["experience"] == 0
            assert survival["experience_for_next_level"] == 150

            crafting = next(s for s in skills if s["name"] == "crafting")
            assert crafting["level"] == 1
            assert crafting["experience"] == 0
            assert crafting["experience_for_next_level"] == 150

            # Check attributes
            attributes = data["attributes"]
            assert len(attributes) == 5
            for attr in attributes:
                assert attr["current_value"] >= attr["base_value"]

    @pytest.mark.asyncio
    async def test_unified_progression_with_character_xp(self):
        """Test unified progression reflects character XP and level-ups."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Grant enough XP for level 2 (150 XP needed)
            await grant_character_xp(session, character, 150)
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/character/progression",
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            char = data["character"]
            assert char["level"] == 2
            assert char["experience"] == 0
            assert char["experience_for_next_level"] == 250  # 2 * 100 + 50
            assert char["progress_percent"] == 0.0
            assert char["attribute_points"] == 1  # 1 point per level-up

    @pytest.mark.asyncio
    async def test_unified_progression_with_skill_xp(self):
        """Test unified progression reflects skill XP and level-ups."""
        await _setup_db()
        # Use NOBLE_DESCENDANT which has no starting skills
        character, game_session = await _create_character_with_session(
            BackgroundName.NOBLE_DESCENDANT
        )
        session_token = game_session.session_token

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Grant skill XP to survival (100 XP = level 1 with 50 remaining)
            await grant_skill_xp(session, character, "survival", 100)
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/character/progression",
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            skills = data["skills"]
            survival = next(s for s in skills if s["name"] == "survival")
            assert survival["level"] == 1
            assert survival["experience"] == 50  # 100 - 50 = 50 remaining
            assert survival["experience_for_next_level"] == 150  # 1 * 100 + 50
            assert survival["progress_percent"] == 33.3  # 50/150 * 100

    @pytest.mark.asyncio
    async def test_unified_progression_with_attribute_allocation(self):
        """Test unified progression reflects attribute point allocation."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Give attribute points and allocate
            character.attribute_points = 3
            await allocate_attribute_points(session, character, "strength", 2)
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/character/progression",
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            char = data["character"]
            assert char["attribute_points"] == 1  # 3 - 2 = 1 remaining

            attributes = data["attributes"]
            strength = next(a for a in attributes if a["name"] == "strength")
            # COMMONER has +1 strength, so base is 11
            assert strength["base_value"] == 11
            assert strength["current_value"] == 13  # 11 + 2

    @pytest.mark.asyncio
    async def test_unified_progression_complete_lifecycle(self):
        """Test complete progression lifecycle across all systems."""
        await _setup_db()
        # Use NOBLE_DESCENDANT which has negotiation:2, magic:1 as starting skills
        character, game_session = await _create_character_with_session(
            BackgroundName.NOBLE_DESCENDANT
        )
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Initial state - NOBLE_DESCENDANT starts with negotiation:2, magic:1
            response = await client.get(
                "/api/character/progression",
                params={"session_token": session_token},
            )
            data = response.json()
            assert data["character"]["level"] == 1
            assert data["character"]["attribute_points"] == 0
            assert len(data["skills"]) == 2  # NOBLE_DESCENDANT has 2 starting skills
            skill_names = [s["name"] for s in data["skills"]]
            assert "negotiation" in skill_names
            assert "magic" in skill_names

            # Grant character XP -> level up -> attribute point
            async with get_session() as session:
                character = await _get_character_in_session(session, character.id)
                await grant_character_xp(session, character, 150)
                await session.commit()

            response = await client.get(
                "/api/character/progression",
                params={"session_token": session_token},
            )
            data = response.json()
            assert data["character"]["level"] == 2
            assert data["character"]["attribute_points"] == 1

            # Grant skill XP to a new skill (swordsmanship)
            async with get_session() as session:
                character = await _get_character_in_session(session, character.id)
                await grant_skill_xp(session, character, "swordsmanship", 75)
                await session.commit()

            response = await client.get(
                "/api/character/progression",
                params={"session_token": session_token},
            )
            data = response.json()
            # Now should have 3 skills (2 starting + 1 new)
            assert len(data["skills"]) == 3
            swordsmanship = next(
                s for s in data["skills"] if s["name"] == "swordsmanship"
            )
            assert swordsmanship["level"] == 1
            assert swordsmanship["experience"] == 25  # 75 - 50 = 25

            # Allocate attribute point
            async with get_session() as session:
                character = await _get_character_in_session(session, character.id)
                await allocate_attribute_points(session, character, "agility", 1)
                await session.commit()

            response = await client.get(
                "/api/character/progression",
                params={"session_token": session_token},
            )
            data = response.json()
            assert data["character"]["attribute_points"] == 0
            agility = next(a for a in data["attributes"] if a["name"] == "agility")
            assert agility["current_value"] == agility["base_value"] + 1


class TestCrossSystemIndependence:
    """Tests verifying cross-system independence."""

    @pytest.mark.asyncio
    async def test_character_xp_does_not_affect_skills(self):
        """Test that character XP does not affect skill progression."""
        await _setup_db()
        # NOBLE_DESCENDANT starts with negotiation:2, magic:1
        character, game_session = await _create_character_with_session(
            BackgroundName.NOBLE_DESCENDANT
        )

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Get initial skills
            skills_result = await session.execute(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character.id
                )
            )
            initial_skills = skills_result.scalars().all()
            initial_skill_count = len(initial_skills)
            initial_skill_names = {s.name.value for s in initial_skills}

            # Grant character XP only
            await grant_character_xp(session, character, 500)
            await session.commit()

            # Check skills unchanged (no new skills created)
            skills_result = await session.execute(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character.id
                )
            )
            skills = skills_result.scalars().all()
            assert len(skills) == initial_skill_count
            skill_names = {s.name.value for s in skills}
            assert skill_names == initial_skill_names  # Same skills, no new ones

    @pytest.mark.asyncio
    async def test_skill_xp_does_not_affect_character_level(self):
        """Test that skill XP does not affect character level."""
        await _setup_db()
        character, game_session = await _create_character_with_session(
            BackgroundName.NOBLE_DESCENDANT
        )

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Grant skill XP only
            await grant_skill_xp(session, character, "survival", 1000)
            await session.commit()

            # Character level should still be 1
            await session.refresh(character)
            assert character.level == 1
            assert character.experience == 0
            assert character.attribute_points == 0

    @pytest.mark.asyncio
    async def test_attribute_points_only_from_character_level(self):
        """Test that attribute points only come from character level-ups."""
        await _setup_db()
        character, game_session = await _create_character_with_session(
            BackgroundName.NOBLE_DESCENDANT
        )

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Grant skill XP to level up multiple skills
            await grant_skill_xp(session, character, "survival", 500)
            await grant_skill_xp(session, character, "trading", 500)
            await grant_skill_xp(session, character, "magic", 500)
            await session.commit()

            # Attribute points should still be 0
            await session.refresh(character)
            assert character.attribute_points == 0

            # Now grant character XP
            await grant_character_xp(session, character, 150)
            await session.commit()

            # Attribute points should be 1
            await session.refresh(character)
            assert character.attribute_points == 1


class TestProgressionPersistence:
    """Tests for progression persistence across requests."""

    @pytest.mark.asyncio
    async def test_progression_persists_across_requests(self):
        """Test that progression data persists after simulated browser refresh."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        # First client - perform some activities
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Work to gain XP
            await client.post(
                "/api/activities/work",
                json={},
                params={"session_token": session_token},
            )

            # Get progression
            response = await client.get(
                "/api/character/progression",
                params={"session_token": session_token},
            )
            data1 = response.json()

        # Second client (simulated refresh) - get progression again
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client2:
            response = await client2.get(
                "/api/character/progression",
                params={"session_token": session_token},
            )
            data2 = response.json()

        # Should be identical
        assert data1["character"]["level"] == data2["character"]["level"]
        assert data1["character"]["experience"] == data2["character"]["experience"]
        assert (
            data1["character"]["attribute_points"]
            == data2["character"]["attribute_points"]
        )
        assert len(data1["skills"]) == len(data2["skills"])
        for s1, s2 in zip(
            sorted(data1["skills"], key=lambda x: x["name"]),
            sorted(data2["skills"], key=lambda x: x["name"]),
        ):
            assert s1["level"] == s2["level"]
            assert s1["experience"] == s2["experience"]
        assert len(data1["attributes"]) == len(data2["attributes"])
        for a1, a2 in zip(
            sorted(data1["attributes"], key=lambda x: x["name"]),
            sorted(data2["attributes"], key=lambda x: x["name"]),
        ):
            assert a1["current_value"] == a2["current_value"]

    @pytest.mark.asyncio
    async def test_attribute_allocation_persists(self):
        """Test that attribute allocation persists after reload."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.attribute_points = 3
            await allocate_attribute_points(session, character, "vitality", 2)
            await session.commit()

        # First request
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/character/progression",
                params={"session_token": session_token},
            )
            data1 = response.json()
            vitality1 = next(a for a in data1["attributes"] if a["name"] == "vitality")
            assert vitality1["current_value"] == vitality1["base_value"] + 2

        # Second request (new client)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client2:
            response = await client2.get(
                "/api/character/progression",
                params={"session_token": session_token},
            )
            data2 = response.json()
            vitality2 = next(a for a in data2["attributes"] if a["name"] == "vitality")
            assert vitality2["current_value"] == vitality2["base_value"] + 2
            assert vitality1["current_value"] == vitality2["current_value"]


class TestProgressionEndpointErrors:
    """Tests for progression endpoint error handling."""

    @pytest.mark.asyncio
    async def test_invalid_session_token(self):
        """Test progression endpoint with invalid session token."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/character/progression",
                params={"session_token": "invalid_token"},
            )
            assert response.status_code == 404
            data = response.json()
            assert data["detail"]["error"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_dead_character_rejected(self):
        """Test that dead characters cannot access progression."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.is_alive = False
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/character/progression",
                params={"session_token": session_token},
            )
            assert response.status_code == 400
            data = response.json()
            assert "Dead characters cannot" in data["detail"]["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
