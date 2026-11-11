"""Tests for character XP and level progression system."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.core.database import get_session, recreate_db
from app.models.enums import RaceName, BackgroundName, GenderPresentation
from app.models.gameplay import Character
from app.services.world import seed_world
from app.services.character.creation import create_character
from app.services.character.progression import (
    grant_character_xp,
    get_character_progression,
)


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


async def _get_character_in_session(session, character_id: int) -> Character:
    """Get character in a specific session."""
    result = await session.execute(
        select(Character).where(Character.id == character_id)
    )
    return result.scalar_one()


class TestGrantCharacterXP:
    """Tests for grant_character_xp function."""

    @pytest.mark.asyncio
    async def test_grant_xp_increases_experience(self):
        """Test that granting XP increases character experience."""
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            # Refresh character to get attached to session
            character = await _get_character_in_session(session, character.id)

            result = await grant_character_xp(session, character, 50)

            assert result["xp_granted"] == 50
            assert result["previous_level"] == 1
            assert result["new_level"] == 1
            assert result["leveled_up"] is False
            assert result["xp_remaining"] == 50
            assert result["xp_for_next_level"] == 150  # 1 * 100 + 50

    @pytest.mark.asyncio
    async def test_grant_xp_levels_up_character(self):
        """Test that granting enough XP levels up character."""
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)

            # Grant enough XP to level up (150 XP needed for level 1 -> 2)
            result = await grant_character_xp(session, character, 150)

            assert result["xp_granted"] == 150
            assert result["previous_level"] == 1
            assert result["new_level"] == 2
            assert result["leveled_up"] is True
            # After level up, 150 - 150 = 0 XP remaining
            assert result["xp_remaining"] == 0
            assert result["xp_for_next_level"] == 250  # 2 * 100 + 50

    @pytest.mark.asyncio
    async def test_grant_xp_multiple_levels(self):
        """Test granting enough XP for multiple level-ups."""
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)

            # Grant XP for 2 levels: 150 (lvl 1->2) + 250 (lvl 2->3) = 400
            result = await grant_character_xp(session, character, 400)

            assert result["xp_granted"] == 400
            assert result["previous_level"] == 1
            assert result["new_level"] == 3
            assert result["leveled_up"] is True
            # 400 - 150 - 250 = 0 XP remaining
            assert result["xp_remaining"] == 0
            assert result["xp_for_next_level"] == 350  # 3 * 100 + 50

    @pytest.mark.asyncio
    async def test_grant_xp_with_remainder(self):
        """Test granting XP leaves remainder after level-up."""
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)

            # Grant 200 XP: 150 for level up, 50 remaining
            result = await grant_character_xp(session, character, 200)

            assert result["xp_granted"] == 200
            assert result["previous_level"] == 1
            assert result["new_level"] == 2
            assert result["leveled_up"] is True
            assert result["xp_remaining"] == 50
            assert result["xp_for_next_level"] == 250

    @pytest.mark.asyncio
    async def test_grant_zero_xp(self):
        """Test granting zero XP does nothing."""
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)

            result = await grant_character_xp(session, character, 0)

            assert result["xp_granted"] == 0
            assert result["previous_level"] == 1
            assert result["new_level"] == 1
            assert result["leveled_up"] is False
            assert result["xp_remaining"] == 0

    @pytest.mark.asyncio
    async def test_grant_negative_xp(self):
        """Test granting negative XP does nothing."""
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)

            result = await grant_character_xp(session, character, -10)

            assert result["xp_granted"] == 0
            assert result["previous_level"] == 1
            assert result["new_level"] == 1
            assert result["leveled_up"] is False


class TestGetCharacterProgression:
    """Tests for get_character_progression function."""

    @pytest.mark.asyncio
    async def test_get_progression_initial(self):
        """Test getting progression for new character."""
        character, game_session = await _create_character_with_session()

        progression = await get_character_progression(character)

        assert progression["level"] == 1
        assert progression["experience"] == 0
        assert progression["experience_for_next_level"] == 150
        assert progression["progress_percent"] == 0.0

    @pytest.mark.asyncio
    async def test_get_progression_after_xp(self):
        """Test getting progression after gaining XP."""
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            await grant_character_xp(session, character, 75)

        progression = await get_character_progression(character)

        assert progression["level"] == 1
        assert progression["experience"] == 75
        assert progression["experience_for_next_level"] == 150
        assert progression["progress_percent"] == 50.0


class TestCharacterProgressionIntegration:
    """Integration tests for character progression with activities."""

    @pytest.mark.asyncio
    async def test_explore_grants_character_xp(self):
        """Test that explore activity grants character XP."""
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Perform explore
            response = await client.post(
                "/api/activities/explore",
                json={},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            # Check character progression info in response
            assert "character_xp_gained" in data["result"]
            assert "character_leveled_up" in data["result"]
            assert "character_level" in data["result"]

            assert data["result"]["character_xp_gained"] == 10
            assert data["result"]["character_leveled_up"] is False
            assert data["result"]["character_level"] == 1

    @pytest.mark.asyncio
    async def test_work_grants_character_xp(self):
        """Test that work activity grants character XP."""
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Perform work
            response = await client.post(
                "/api/activities/work", json={}, params={"session_token": session_token}
            )
            assert response.status_code == 200
            data = response.json()

            # Check character progression info in response
            assert "character_xp_gained" in data["result"]
            assert "character_leveled_up" in data["result"]
            assert "character_level" in data["result"]

            assert data["result"]["character_xp_gained"] == 15
            assert data["result"]["character_leveled_up"] is False
            assert data["result"]["character_level"] == 1

    @pytest.mark.asyncio
    async def test_progression_persistence(self):
        """Test that character progression persists across requests."""
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Perform work multiple times
            for _ in range(3):
                await client.post(
                    "/api/activities/work",
                    json={},
                    params={"session_token": session_token},
                )

            # Create new client (simulating browser refresh)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client2:
                # Check time state (progression is stored in character, not time)
                # But we can verify character level by doing another activity
                response = await client2.post(
                    "/api/activities/work",
                    json={},
                    params={"session_token": session_token},
                )
                assert response.status_code == 200
                data = response.json()

                # After 3 works (15 XP each = 45 XP), should still be level 1
                # 4th work adds 15 more = 60 XP total, still level 1
                assert data["result"]["character_level"] == 1

    @pytest.mark.asyncio
    async def test_level_up_narrative_in_explore(self):
        """Test that level-up narrative is included in explore response."""
        # Create character with XP close to level up
        async with get_session() as session:
            character, game_session = await create_character(
                session=session,
                name="Test Character",
                race_name=RaceName.HUMAN,
                background_name=BackgroundName.COMMONER,
                gender_presentation=GenderPresentation.MALE,
            )
            session_token = game_session.session_token
            # Manually set XP close to level up
            character.experience = 145
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Explore grants 10 XP, should trigger level up (145 + 10 = 155 >= 150)
            response = await client.post(
                "/api/activities/explore",
                json={},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            # Should have leveled up
            assert data["result"]["character_leveled_up"] is True
            assert data["result"]["character_level"] == 2
            # Narrative should mention level up
            assert "level 2" in data["result"]["narrative"]

    @pytest.mark.asyncio
    async def test_level_up_narrative_in_work(self):
        """Test that level-up narrative is included in work response."""
        # Create character with XP close to level up
        async with get_session() as session:
            character, game_session = await create_character(
                session=session,
                name="Test Character",
                race_name=RaceName.HUMAN,
                background_name=BackgroundName.COMMONER,
                gender_presentation=GenderPresentation.MALE,
            )
            session_token = game_session.session_token
            # Manually set XP close to level up
            character.experience = 140
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Work grants 15 XP, should trigger level up (140 + 15 = 155 >= 150)
            response = await client.post(
                "/api/activities/work", json={}, params={"session_token": session_token}
            )
            assert response.status_code == 200
            data = response.json()

            # Should have leveled up
            assert data["result"]["character_leveled_up"] is True
            assert data["result"]["character_level"] == 2
            # Narrative should mention level up
            assert "level 2" in data["result"]["narrative"]


class TestCharacterModelProgression:
    """Tests for Character model progression properties."""

    @pytest.mark.asyncio
    async def test_experience_for_next_level_formula(self):
        """Test that experience_for_next_level uses correct formula."""
        character, game_session = await _create_character_with_session()

        # Level 1: 1 * 100 + 50 = 150
        assert character.experience_for_next_level == 150

        # Simulate level 2
        character.level = 2
        assert character.experience_for_next_level == 250  # 2 * 100 + 50

        # Simulate level 10
        character.level = 10
        assert character.experience_for_next_level == 1050  # 10 * 100 + 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
