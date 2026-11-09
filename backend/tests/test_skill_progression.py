"""Tests for skill XP and level progression system."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.core.database import get_session, recreate_db
from app.models.enums import RaceName, BackgroundName, GenderPresentation, SkillName
from app.models.gameplay import Character, CharacterSkill
from app.services.world import seed_world
from app.services.character.creation import create_character
from app.services.character.progression import (
    grant_skill_xp,
    get_skill_progression_from_skill,
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


class TestGrantSkillXP:
    """Tests for grant_skill_xp function."""

    @pytest.mark.asyncio
    async def test_grant_xp_increases_experience(self):
        """Test that granting XP increases skill experience."""
        # Use MERCHANT_FAMILY background which doesn't have survival skill
        character, game_session = await _create_character_with_session(
            BackgroundName.MERCHANT_FAMILY
        )

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)

            result = await grant_skill_xp(session, character, "survival", 25)

            assert result["skill_name"] == "survival"
            assert result["xp_granted"] == 25
            assert result["previous_level"] == 0
            assert result["new_level"] == 0
            assert result["leveled_up"] is False
            assert result["xp_remaining"] == 25
            assert result["xp_for_next_level"] == 50  # 0 * 100 + 50

    @pytest.mark.asyncio
    async def test_grant_xp_levels_up_skill(self):
        """Test that granting enough XP levels up skill."""
        character, game_session = await _create_character_with_session(
            BackgroundName.MERCHANT_FAMILY
        )

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)

            # Grant enough XP to level up (50 XP needed for level 0 -> 1)
            result = await grant_skill_xp(session, character, "survival", 50)

            assert result["skill_name"] == "survival"
            assert result["xp_granted"] == 50
            assert result["previous_level"] == 0
            assert result["new_level"] == 1
            assert result["leveled_up"] is True
            # After level up, 50 - 50 = 0 XP remaining
            assert result["xp_remaining"] == 0
            assert result["xp_for_next_level"] == 150  # 1 * 100 + 50

    @pytest.mark.asyncio
    async def test_grant_xp_multiple_levels(self):
        """Test granting enough XP for multiple level-ups."""
        character, game_session = await _create_character_with_session(
            BackgroundName.MERCHANT_FAMILY
        )

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)

            # Grant XP for 2 levels: 50 (lvl 0->1) + 150 (lvl 1->2) = 200
            result = await grant_skill_xp(session, character, "survival", 200)

            assert result["skill_name"] == "survival"
            assert result["xp_granted"] == 200
            assert result["previous_level"] == 0
            assert result["new_level"] == 2
            assert result["leveled_up"] is True
            # 200 - 50 - 150 = 0 XP remaining
            assert result["xp_remaining"] == 0
            assert result["xp_for_next_level"] == 250  # 2 * 100 + 50

    @pytest.mark.asyncio
    async def test_grant_xp_with_remainder(self):
        """Test granting XP leaves remainder after level-up."""
        character, game_session = await _create_character_with_session(
            BackgroundName.MERCHANT_FAMILY
        )

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)

            # Grant 75 XP: 50 for level up, 25 remaining
            result = await grant_skill_xp(session, character, "survival", 75)

            assert result["skill_name"] == "survival"
            assert result["xp_granted"] == 75
            assert result["previous_level"] == 0
            assert result["new_level"] == 1
            assert result["leveled_up"] is True
            assert result["xp_remaining"] == 25
            assert result["xp_for_next_level"] == 150

    @pytest.mark.asyncio
    async def test_grant_zero_xp(self):
        """Test granting zero XP does nothing."""
        character, game_session = await _create_character_with_session(
            BackgroundName.MERCHANT_FAMILY
        )

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)

            result = await grant_skill_xp(session, character, "survival", 0)

            assert result["skill_name"] == "survival"
            assert result["xp_granted"] == 0
            assert result["previous_level"] == 0
            assert result["new_level"] == 0
            assert result["leveled_up"] is False
            assert result["xp_remaining"] == 0

    @pytest.mark.asyncio
    async def test_grant_negative_xp(self):
        """Test granting negative XP does nothing."""
        character, game_session = await _create_character_with_session(
            BackgroundName.MERCHANT_FAMILY
        )

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)

            result = await grant_skill_xp(session, character, "survival", -10)

            assert result["skill_name"] == "survival"
            assert result["xp_granted"] == 0
            assert result["previous_level"] == 0
            assert result["new_level"] == 0
            assert result["leveled_up"] is False

    @pytest.mark.asyncio
    async def test_grant_xp_creates_new_skill(self):
        """Test granting XP creates skill if it doesn't exist."""
        character, game_session = await _create_character_with_session(
            BackgroundName.MERCHANT_FAMILY
        )

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)

            # Grant XP to a skill the character doesn't have yet
            result = await grant_skill_xp(session, character, "magic", 30)

            assert result["skill_name"] == "magic"
            assert result["xp_granted"] == 30
            assert result["previous_level"] == 0
            assert result["new_level"] == 0
            assert result["leveled_up"] is False
            assert result["xp_remaining"] == 30

            # Verify skill was created in database
            skill = await _get_skill_in_session(session, character.id, SkillName.MAGIC)
            assert skill is not None
            assert skill.level == 0
            assert skill.experience == 30

    @pytest.mark.asyncio
    async def test_different_skills_independent(self):
        """Test that different skills progress independently."""
        # Use NOBLE_DESCENDANT which has neither survival nor trading as starting skills
        character, game_session = await _create_character_with_session(
            BackgroundName.NOBLE_DESCENDANT
        )

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)

            # Grant XP to survival
            await grant_skill_xp(session, character, "survival", 100)

            # Grant XP to trading
            await grant_skill_xp(session, character, "trading", 50)

            # Check survival - 100 XP = level 1 (50 for lvl 0->1, 50 remaining)
            survival = await _get_skill_in_session(
                session, character.id, SkillName.SURVIVAL
            )
            assert survival.level == 1
            assert survival.experience == 50

            # Check trading - 50 XP = exactly enough for level 1 (50 for lvl 0->1, 0 remaining)
            trading = await _get_skill_in_session(
                session, character.id, SkillName.TRADING
            )
            assert trading.level == 1
            assert trading.experience == 0


class TestGetSkillProgression:
    """Tests for get_skill_progression_from_skill function."""

    @pytest.mark.asyncio
    async def test_get_progression_initial(self):
        """Test getting progression for new skill."""
        character, game_session = await _create_character_with_session(
            BackgroundName.MERCHANT_FAMILY
        )

        # Skill doesn't exist yet
        progression = get_skill_progression_from_skill(None)

        assert progression["name"] == ""
        assert progression["level"] == 0
        assert progression["experience"] == 0
        assert progression["experience_for_next_level"] == 50
        assert progression["progress_percent"] == 0.0

    @pytest.mark.asyncio
    async def test_get_progression_after_xp(self):
        """Test getting progression after gaining XP."""
        character, game_session = await _create_character_with_session(
            BackgroundName.MERCHANT_FAMILY
        )

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            await grant_skill_xp(session, character, "survival", 75)

            # Get the skill
            skill = await _get_skill_in_session(
                session, character.id, SkillName.SURVIVAL
            )

        progression = get_skill_progression_from_skill(skill)

        assert progression["name"] == "survival"
        assert progression["level"] == 1  # 75 XP = level 1
        assert progression["experience"] == 25  # 75 - 50 = 25 remaining
        assert progression["experience_for_next_level"] == 150
        assert progression["progress_percent"] == 16.7  # 25/150 * 100


class TestSkillProgressionIntegration:
    """Integration tests for skill progression with activities."""

    @pytest.mark.asyncio
    async def test_explore_grants_survival_xp_and_progression(self):
        """Test that explore activity grants survival XP and includes skill progression."""
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

            # Check skill progression info in response
            assert "skill_progression" in data["result"]
            assert "survival" in data["result"]["skill_progression"]
            survival_prog = data["result"]["skill_progression"]["survival"]

            assert survival_prog["xp_gained"] >= 5  # Base survival XP
            assert "level" in survival_prog
            assert "leveled_up" in survival_prog
            # COMMONER starts with survival at level 1, so first explore (5 XP) won't level up (needs 150 for level 2)
            assert survival_prog["leveled_up"] is False
            assert survival_prog["level"] == 1

    @pytest.mark.asyncio
    async def test_work_grants_skill_xp_and_progression(self):
        """Test that work activity grants skill XP and includes skill progression."""
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

            # Check skill progression info in response
            assert "skill_progression" in data["result"]
            # Should have at least one skill with progression
            assert len(data["result"]["skill_progression"]) > 0

            for skill_name, prog in data["result"]["skill_progression"].items():
                assert "xp_gained" in prog
                assert "level" in prog
                assert "leveled_up" in prog

    @pytest.mark.asyncio
    async def test_progression_persistence(self):
        """Test that skill progression persists across requests."""
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
                # Do another work and check skill progression
                response = await client2.post(
                    "/api/activities/work",
                    json={},
                    params={"session_token": session_token},
                )
                assert response.status_code == 200
                data = response.json()

                # Skill progression should be present
                assert "skill_progression" in data["result"]

    @pytest.mark.asyncio
    async def test_skill_level_up_narrative_in_explore(self):
        """Test that skill level-up narrative is included in explore response."""
        # Create character with survival XP close to level up
        # COMMONER starts with survival at level 1, so we need 150 XP for level 2
        async with get_session() as session:
            character, game_session = await create_character(
                session=session,
                name="Test Character",
                race_name=RaceName.HUMAN,
                background_name=BackgroundName.COMMONER,
                gender_presentation=GenderPresentation.MALE,
            )
            session_token = game_session.session_token
            # Update the existing survival skill (COMMONER starts with it at level 1)
            result = await session.execute(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character.id,
                    CharacterSkill.name == SkillName.SURVIVAL,
                )
            )
            skill = result.scalar_one()
            skill.experience = 145
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Explore grants 5 survival XP, should trigger level up (145 + 5 = 150 >= 150)
            response = await client.post(
                "/api/activities/explore",
                json={},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            # Should have leveled up survival
            survival_prog = data["result"]["skill_progression"]["survival"]
            assert survival_prog["leveled_up"] is True
            assert survival_prog["level"] == 2
            # Narrative should mention skill level up
            assert "survival skill has reached level 2" in data["result"]["narrative"]

    @pytest.mark.asyncio
    async def test_skill_level_up_narrative_in_work(self):
        """Test that skill level-up narrative is included in work response."""
        # Create character with skill XP close to level up
        # COMMONER starts with survival at level 1, so we need 150 XP for level 2
        async with get_session() as session:
            character, game_session = await create_character(
                session=session,
                name="Test Character",
                race_name=RaceName.HUMAN,
                background_name=BackgroundName.COMMONER,
                gender_presentation=GenderPresentation.MALE,
            )
            session_token = game_session.session_token
            # Update the existing survival skill (COMMONER starts with it at level 1)
            result = await session.execute(
                select(CharacterSkill).where(
                    CharacterSkill.character_id == character.id,
                    CharacterSkill.name == SkillName.SURVIVAL,
                )
            )
            skill = result.scalar_one()
            skill.experience = 140
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Work as Laborer grants 10 + 1*2 = 12 survival XP, should trigger level up (140 + 12 = 152 >= 150)
            response = await client.post(
                "/api/activities/work",
                json={"work_type": "Laborer"},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            # Should have leveled up survival
            survival_prog = data["result"]["skill_progression"]["survival"]
            assert survival_prog["leveled_up"] is True
            assert survival_prog["level"] == 2
            # Narrative should mention skill level up
            assert "survival skill has reached level 2" in data["result"]["narrative"]


class TestCharacterModelSkillProgression:
    """Tests for CharacterSkill model progression properties."""

    @pytest.mark.asyncio
    async def test_experience_for_next_level_formula(self):
        """Test that experience_for_next_level uses correct formula."""
        character, game_session = await _create_character_with_session(
            BackgroundName.MERCHANT_FAMILY
        )

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)

            # Create a skill at level 0
            skill = CharacterSkill(
                character_id=character.id,
                name=SkillName.SURVIVAL,
                level=0,
                experience=0,
            )
            session.add(skill)
            await session.flush()

            # Level 0: 0 * 100 + 50 = 50
            assert skill.experience_for_next_level == 50

            # Simulate level 1
            skill.level = 1
            assert skill.experience_for_next_level == 150  # 1 * 100 + 50

            # Simulate level 5
            skill.level = 5
            assert skill.experience_for_next_level == 550  # 5 * 100 + 50

    @pytest.mark.asyncio
    async def test_character_xp_and_skill_xp_separate(self):
        """Test that character XP and skill XP are separate."""
        character, game_session = await _create_character_with_session(
            BackgroundName.MERCHANT_FAMILY
        )

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)

            # Grant character XP
            from app.services.character.progression import grant_character_xp

            await grant_character_xp(session, character, 100)

            # Grant skill XP
            await grant_skill_xp(session, character, "survival", 100)

            # Check character level
            assert (
                character.level == 1
            )  # 100 XP -> level 1 (150 needed for lvl 1->2, so 100 is still lvl 1)
            assert character.experience == 100

            # Check skill level
            skill = await _get_skill_in_session(
                session, character.id, SkillName.SURVIVAL
            )
            assert skill.level == 1  # 100 XP -> level 1 (50 for lvl 0->1, 50 remaining)
            assert skill.experience == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
