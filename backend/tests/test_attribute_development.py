"""Tests for attribute development system."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.core.database import get_session, recreate_db
from app.models.enums import RaceName, BackgroundName, GenderPresentation, AttributeName
from app.models.gameplay import Character, CharacterAttribute
from app.services.world import seed_world
from app.services.character.creation import create_character
from app.services.character.progression import (
    grant_character_xp,
    allocate_attribute_points,
)


async def _setup_db():
    """Set up database with world data."""
    await recreate_db()
    async with get_session() as session:
        await seed_world(session)
        return session


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


async def _get_character_in_session(session, character_id: int) -> Character:
    """Get character in a specific session."""
    result = await session.execute(
        select(Character).where(Character.id == character_id)
    )
    return result.scalar_one()


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


class TestAttributePointsInitial:
    """Tests for initial attribute points."""

    @pytest.mark.asyncio
    async def test_initial_attribute_points_zero(self):
        """Test that new characters start with 0 attribute points."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            assert character.attribute_points == 0

    @pytest.mark.asyncio
    async def test_get_attribute_points_endpoint(self):
        """Test getting attribute points via API."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/character/attribute-points",
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["attribute_points"] == 0


class TestAttributePointsFromLevelUp:
    """Tests for earning attribute points through level-ups."""

    @pytest.mark.asyncio
    async def test_level_up_grants_attribute_point(self):
        """Test that character level-up awards 1 attribute point."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Grant enough XP to level up (150 XP needed for level 1 -> 2)
            result = await grant_character_xp(session, character, 150)

            assert result["xp_granted"] == 150
            assert result["previous_level"] == 1
            assert result["new_level"] == 2
            assert result["leveled_up"] is True
            assert result["attribute_points_gained"] == 1
            # Check character has the attribute point
            await session.refresh(character)
            assert character.attribute_points == 1

    @pytest.mark.asyncio
    async def test_multiple_level_ups_grant_multiple_points(self):
        """Test that multiple level-ups award correct number of points."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Grant XP for 2 levels: 150 (lvl 1->2) + 250 (lvl 2->3) = 400
            result = await grant_character_xp(session, character, 400)

            assert result["xp_granted"] == 400
            assert result["previous_level"] == 1
            assert result["new_level"] == 3
            assert result["leveled_up"] is True
            assert result["attribute_points_gained"] == 2
            # Check character has the attribute points
            await session.refresh(character)
            assert character.attribute_points == 2

    @pytest.mark.asyncio
    async def test_skill_level_up_no_attribute_points(self):
        """Test that skill level-ups do not award attribute points."""
        from app.services.character.progression import grant_skill_xp

        # Use NOBLE_DESCENDANT which has no survival skill
        await _setup_db()
        async with get_session() as session:
            character, game_session = await create_character(
                session=session,
                name="Test Character",
                race_name=RaceName.HUMAN,
                background_name=BackgroundName.NOBLE_DESCENDANT,
                gender_presentation=GenderPresentation.MALE,
            )

            # Grant skill XP to level up a skill (survival starts at level 0 for NOBLE_DESCENDANT)
            result = await grant_skill_xp(session, character, "survival", 50)

            assert result["leveled_up"] is True
            # Check character still has 0 attribute points
            await session.refresh(character)
            assert character.attribute_points == 0

    @pytest.mark.asyncio
    async def test_explore_grants_attribute_point_on_level_up(self):
        """Test that explore activity grants attribute point on character level up."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        # Manually set character XP close to level up
        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.experience = 145  # 150 needed for level 1->2
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Explore grants 10 character XP, should trigger level up
            response = await client.post(
                "/api/activities/explore",
                json={},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            assert data["result"]["character_leveled_up"] is True
            assert data["result"]["character_level"] == 2
            assert data["result"]["attribute_points_gained"] == 1

    @pytest.mark.asyncio
    async def test_work_grants_attribute_point_on_level_up(self):
        """Test that work activity grants attribute point on character level up."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        # Manually set character XP close to level up
        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.experience = 140  # 150 needed for level 1->2, work gives 15 XP
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Work grants 15 character XP, should trigger level up
            response = await client.post(
                "/api/activities/work", json={}, params={"session_token": session_token}
            )
            assert response.status_code == 200
            data = response.json()

            assert data["result"]["character_leveled_up"] is True
            assert data["result"]["character_level"] == 2
            assert data["result"]["attribute_points_gained"] == 1


class TestAttributeAllocation:
    """Tests for allocating attribute points."""

    @pytest.mark.asyncio
    async def test_allocate_single_point(self):
        """Test allocating a single attribute point."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Give character attribute points
            character.attribute_points = 3
            await session.flush()

            # Get initial strength
            attr = await _get_attribute_in_session(
                session, character.id, AttributeName.STRENGTH
            )
            initial_value = attr.current_value

            # Allocate 1 point to strength
            result = await allocate_attribute_points(session, character, "strength", 1)

            assert result["attribute_name"] == "strength"
            assert result["points_allocated"] == 1
            assert result["previous_value"] == initial_value
            assert result["new_value"] == initial_value + 1
            assert result["remaining_points"] == 2

            # Verify in database
            attr = await _get_attribute_in_session(
                session, character.id, AttributeName.STRENGTH
            )
            assert attr.current_value == initial_value + 1
            await session.refresh(character)
            assert character.attribute_points == 2

    @pytest.mark.asyncio
    async def test_allocate_multiple_points(self):
        """Test allocating multiple attribute points at once."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.attribute_points = 5
            await session.flush()

            # Get initial agility
            attr = await _get_attribute_in_session(
                session, character.id, AttributeName.AGILITY
            )
            initial_value = attr.current_value

            # Allocate 3 points to agility
            result = await allocate_attribute_points(session, character, "agility", 3)

            assert result["attribute_name"] == "agility"
            assert result["points_allocated"] == 3
            assert result["previous_value"] == initial_value
            assert result["new_value"] == initial_value + 3
            assert result["remaining_points"] == 2

    @pytest.mark.asyncio
    async def test_allocate_to_different_attributes(self):
        """Test allocating points to different attributes independently."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.attribute_points = 5
            await session.flush()

            # Get initial values
            strength_attr = await _get_attribute_in_session(
                session, character.id, AttributeName.STRENGTH
            )
            intelligence_attr = await _get_attribute_in_session(
                session, character.id, AttributeName.INTELLIGENCE
            )
            initial_strength = strength_attr.current_value
            initial_intelligence = intelligence_attr.current_value

            # Allocate to strength
            await allocate_attribute_points(session, character, "strength", 2)
            # Allocate to intelligence
            await allocate_attribute_points(session, character, "intelligence", 2)

            # Check both
            strength = await _get_attribute_in_session(
                session, character.id, AttributeName.STRENGTH
            )
            intelligence = await _get_attribute_in_session(
                session, character.id, AttributeName.INTELLIGENCE
            )

            assert strength.current_value == initial_strength + 2
            assert intelligence.current_value == initial_intelligence + 2
            await session.refresh(character)
            assert character.attribute_points == 1

    @pytest.mark.asyncio
    async def test_insufficient_points_rejected(self):
        """Test that allocation fails when character has insufficient points."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.attribute_points = 1
            await session.flush()

            # Try to allocate 2 points
            with pytest.raises(Exception) as exc_info:
                await allocate_attribute_points(session, character, "strength", 2)

            assert "Insufficient attribute points" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_attribute_name_rejected(self):
        """Test that invalid attribute names are rejected."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.attribute_points = 3
            await session.flush()

            with pytest.raises(Exception) as exc_info:
                await allocate_attribute_points(session, character, "invalid_attr", 1)

            assert "Invalid attribute name" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_zero_points_rejected(self):
        """Test that allocating zero points is rejected."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.attribute_points = 3
            await session.flush()

            with pytest.raises(Exception) as exc_info:
                await allocate_attribute_points(session, character, "strength", 0)

            assert "must be positive" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_negative_points_rejected(self):
        """Test that allocating negative points is rejected."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.attribute_points = 3
            await session.flush()

            with pytest.raises(Exception) as exc_info:
                await allocate_attribute_points(session, character, "strength", -1)

            assert "must be positive" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_attribute_cap_enforced(self):
        """Test that attribute cap is enforced."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.attribute_points = 25
            await session.flush()

            # Try to allocate beyond cap (MAX_ATTRIBUTE_VALUE = 30)
            # Base is 10, so max allocation is 20
            with pytest.raises(Exception) as exc_info:
                await allocate_attribute_points(session, character, "strength", 21)

            assert "exceed maximum value" in str(exc_info.value)


class TestAttributeAllocationAPI:
    """Integration tests for attribute allocation API."""

    @pytest.mark.asyncio
    async def test_allocate_attribute_via_api(self):
        """Test allocating attribute points through the API."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        # Manually set attribute points
        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.attribute_points = 3
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Allocate 1 point to strength
            response = await client.post(
                "/api/character/allocate-attribute",
                json={"attribute_name": "strength", "points": 1},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            assert data["attribute_name"] == "strength"
            assert data["points_allocated"] == 1
            # COMMONER background gives +1 strength, so base is 11
            assert data["new_value"] == 12  # base 11 + 1
            assert data["remaining_points"] == 2

    @pytest.mark.asyncio
    async def test_allocate_multiple_points_via_api(self):
        """Test allocating multiple points through the API."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.attribute_points = 5
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/character/allocate-attribute",
                json={"attribute_name": "agility", "points": 3},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            assert data["points_allocated"] == 3
            assert data["remaining_points"] == 2

    @pytest.mark.asyncio
    async def test_api_insufficient_points(self):
        """Test API rejects allocation with insufficient points."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Character has 0 attribute points initially
            response = await client.post(
                "/api/character/allocate-attribute",
                json={"attribute_name": "strength", "points": 1},
                params={"session_token": session_token},
            )
            assert response.status_code == 400
            data = response.json()
            assert "Insufficient attribute points" in data["detail"]["message"]

    @pytest.mark.asyncio
    async def test_api_invalid_attribute(self):
        """Test API rejects invalid attribute name."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.attribute_points = 3
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/character/allocate-attribute",
                json={"attribute_name": "invalid", "points": 1},
                params={"session_token": session_token},
            )
            assert response.status_code == 400
            data = response.json()
            assert "Invalid attribute name" in data["detail"]["message"]

    @pytest.mark.asyncio
    async def test_api_zero_points(self):
        """Test API rejects zero points allocation."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.attribute_points = 3
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/character/allocate-attribute",
                json={"attribute_name": "strength", "points": 0},
                params={"session_token": session_token},
            )
            assert response.status_code == 422  # Validation error from Pydantic

    @pytest.mark.asyncio
    async def test_api_dead_character_rejected(self):
        """Test that dead characters cannot allocate attribute points."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.is_alive = False
            character.attribute_points = 3
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/character/allocate-attribute",
                json={"attribute_name": "strength", "points": 1},
                params={"session_token": session_token},
            )
            assert response.status_code == 400
            data = response.json()
            assert "Dead characters cannot allocate" in data["detail"]["message"]


class TestAttributePersistence:
    """Tests for attribute persistence across requests."""

    @pytest.mark.asyncio
    async def test_attribute_points_persist(self):
        """Test that attribute points persist after reloading character."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Get initial strength
            strength_attr = await _get_attribute_in_session(
                session, character.id, AttributeName.STRENGTH
            )
            initial_strength = strength_attr.current_value
            # Give attribute points and allocate some
            character.attribute_points = 5
            await allocate_attribute_points(session, character, "strength", 2)
            await session.commit()

        # Reload character in new session
        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            assert character.attribute_points == 3
            strength = await _get_attribute_in_session(
                session, character.id, AttributeName.STRENGTH
            )
            assert strength.current_value == initial_strength + 2

    @pytest.mark.asyncio
    async def test_attribute_allocation_persists(self):
        """Test that allocated attributes persist after reloading."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.attribute_points = 3
            await allocate_attribute_points(session, character, "vitality", 2)
            await session.commit()

        # Simulate browser refresh - new client
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/character/attribute-points",
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["attribute_points"] == 1

            # Check character response includes attribute_points
            # (via character creation response or other endpoint)
            pass


class TestCharacterResponseIncludesAttributePoints:
    """Tests that character responses include attribute_points."""

    @pytest.mark.asyncio
    async def test_character_creation_response_includes_attribute_points(self):
        """Test that character creation response includes attribute_points."""
        await _setup_db()
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
            assert "character" in data
            assert "attribute_points" in data["character"]
            assert data["character"]["attribute_points"] == 0


class TestIndependence:
    """Tests that attribute points are independent from character XP and skill XP."""

    @pytest.mark.asyncio
    async def test_character_xp_and_attribute_points_separate(self):
        """Test that character XP and attribute points are tracked separately."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)

            # Grant character XP (10 XP, not enough for level up)
            result = await grant_character_xp(session, character, 10)
            assert result["attribute_points_gained"] == 0
            await session.refresh(character)
            assert character.attribute_points == 0
            assert character.experience == 10

    @pytest.mark.asyncio
    async def test_skill_xp_and_attribute_points_separate(self):
        """Test that skill XP and attribute points are tracked separately."""
        from app.services.character.progression import grant_skill_xp

        # Use NOBLE_DESCENDANT which has no survival skill
        await _setup_db()
        async with get_session() as session:
            character, game_session = await create_character(
                session=session,
                name="Test Character",
                race_name=RaceName.HUMAN,
                background_name=BackgroundName.NOBLE_DESCENDANT,
                gender_presentation=GenderPresentation.MALE,
            )

            # Grant skill XP
            result = await grant_skill_xp(session, character, "survival", 100)
            assert (
                result["leveled_up"] is True
            )  # 100 XP -> level 1 (50) + level 2 (50 remaining... no, level 2 needs 150)
            # 100 XP: 50 for lvl 0->1, 50 remaining, not enough for lvl 1->2 (150)
            # So level 1 with 50 XP
            await session.refresh(character)
            assert character.attribute_points == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
