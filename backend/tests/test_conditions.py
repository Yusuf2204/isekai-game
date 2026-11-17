"""Tests for character conditions (injuries/sickness)."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.core.database import get_session, recreate_db
from app.models.enums import RaceName, BackgroundName, GenderPresentation
from app.models.gameplay import Character
from app.services.world import seed_world
from app.services.character.creation import create_character
from app.services.character.conditions import (
    add_condition,
    remove_condition,
    get_character_conditions,
    get_all_conditions,
    treat_condition,
    apply_condition_effects,
    reduce_condition_duration,
    generate_injury_from_damage,
    generate_illness_from_exposure,
    calculate_total_penalties,
    get_effective_stamina,
    CONDITIONS,
)
from app.services.character.inventory import (
    get_all_treatments as TREATMENTS,
    get_item_count,
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


class TestConditionDefinitions:
    """Tests for condition definitions."""

    def test_conditions_defined(self):
        """Test that all expected conditions are defined."""
        expected_conditions = [
            "minor_cut",
            "deep_wound",
            "broken_bone",
            "concussion",
            "minor_illness",
            "serious_illness",
            "poison",
            "burn",
            "frostbite",
            "exhaustion",
        ]
        for cond in expected_conditions:
            assert cond in CONDITIONS
            assert "name" in CONDITIONS[cond]
            assert "description" in CONDITIONS[cond]
            assert "base_severity" in CONDITIONS[cond]
            assert "max_duration" in CONDITIONS[cond]
            assert "health_per_period" in CONDITIONS[cond]
            assert "stamina_penalty" in CONDITIONS[cond]
            assert "attribute_penalties" in CONDITIONS[cond]

    @pytest.mark.asyncio
    async def test_treatments_defined(self):
        """Test that all expected treatments are defined."""
        expected_treatments = [
            "bandage",
            "healing_herbs",
            "antidote",
            "splint",
            "medicine",
            "salve",
            "rest_remedy",
        ]
        # TREATMENTS is now a function that returns a dict
        treatments_dict = await TREATMENTS()
        for treat in expected_treatments:
            assert treat in treatments_dict
            assert "name" in treatments_dict[treat]
            assert "treats" in treatments_dict[treat]
            assert "severity_reduction" in treatments_dict[treat]
            assert "description" in treatments_dict[treat]


class TestConditionService:
    """Tests for condition service functions."""

    @pytest.mark.asyncio
    async def test_add_condition(self):
        """Test adding a condition to a character."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            result = await add_condition(session, character, "minor_cut")

            assert result["name"] == "Minor Cut"
            assert result["severity"] == 1
            assert result["duration"] == 3
            assert "minor_cut" in character.conditions

    @pytest.mark.asyncio
    async def test_add_unknown_condition_fails(self):
        """Test adding unknown condition raises error."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            with pytest.raises(Exception) as exc_info:
                await add_condition(session, character, "unknown_condition")
            assert "Unknown condition" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_condition_worsens_existing(self):
        """Test adding same condition worsens it."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            await add_condition(session, character, "minor_cut")
            await add_condition(session, character, "minor_cut")

            condition = character.conditions["minor_cut"]
            assert condition["severity"] == 2  # Worsened from 1 to 2

    @pytest.mark.asyncio
    async def test_remove_condition(self):
        """Test removing a condition."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            await add_condition(session, character, "minor_cut")
            assert "minor_cut" in character.conditions

            removed = await remove_condition(session, character, "minor_cut")
            assert removed is True
            assert "minor_cut" not in character.conditions

    @pytest.mark.asyncio
    async def test_remove_nonexistent_condition(self):
        """Test removing nonexistent condition returns False."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            removed = await remove_condition(session, character, "minor_cut")
            assert removed is False

    @pytest.mark.asyncio
    async def test_get_character_conditions(self):
        """Test getting all conditions for a character."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            await add_condition(session, character, "minor_cut")
            await add_condition(session, character, "deep_wound")

            conditions = await get_character_conditions(character)
            assert len(conditions) == 2
            cond_ids = [c["id"] for c in conditions]
            assert "minor_cut" in cond_ids
            assert "deep_wound" in cond_ids

    @pytest.mark.asyncio
    async def test_get_all_conditions(self):
        """Test getting all condition definitions."""
        conditions = await get_all_conditions()
        assert len(conditions) == len(CONDITIONS)
        for cond_id, cond in conditions.items():
            assert cond_id in CONDITIONS
            assert cond["name"] == CONDITIONS[cond_id]["name"]


class TestConditionEffects:
    """Tests for condition effects application."""

    @pytest.mark.asyncio
    async def test_apply_condition_effects_health_loss(self):
        """Test conditions apply health loss per period."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = 100
            character.max_health = 100
            await session.flush()

            # Add deep wound (-2 health per period)
            await add_condition(session, character, "deep_wound")
            await session.commit()

            # Apply effects
            result = await apply_condition_effects(session, character)
            assert result["health_change"] == -2

    @pytest.mark.asyncio
    async def test_apply_condition_effects_stamina_penalty(self):
        """Test conditions apply stamina penalty."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            await add_condition(session, character, "deep_wound")  # 10 stamina penalty
            await session.commit()

            result = await apply_condition_effects(session, character)
            assert result["stamina_penalty"] == 10

    @pytest.mark.asyncio
    async def test_apply_condition_effects_attribute_penalties(self):
        """Test conditions apply attribute penalties."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            await add_condition(
                session, character, "concussion"
            )  # intelligence -3, agility -2
            await session.commit()

            result = await apply_condition_effects(session, character)
            assert result["attribute_penalties"]["intelligence"] == -3
            assert result["attribute_penalties"]["agility"] == -2

    @pytest.mark.asyncio
    async def test_calculate_total_penalties(self):
        """Test calculating total penalties from conditions and fatigue."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.fatigue_level = 2
            await add_condition(session, character, "minor_cut")  # stamina penalty 0
            await add_condition(session, character, "deep_wound")  # stamina penalty 10
            await session.commit()

            penalties = await calculate_total_penalties(character)
            # deep_wound (10) + fatigue (2*5=10) = 20
            assert penalties["stamina_penalty"] == 20
            # fatigue: -2 to each attribute, deep_wound: agility -2, strength -1
            assert (
                penalties["attribute_penalties"]["agility"] == -4
            )  # -2 from fatigue, -2 from deep_wound
            assert (
                penalties["attribute_penalties"]["strength"] == -3
            )  # -2 from fatigue, -1 from deep_wound

    @pytest.mark.asyncio
    async def test_get_effective_stamina(self):
        """Test getting effective max stamina after penalties."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.max_stamina = 100
            character.fatigue_level = 2
            await add_condition(session, character, "deep_wound")  # 10 stamina penalty
            await session.commit()

            effective = await get_effective_stamina(character)
            # 100 - 10 (condition) - 10 (fatigue 2*5) = 80
            assert effective == 80


class TestConditionTreatment:
    """Tests for treating conditions."""

    @pytest.mark.asyncio
    async def test_treat_condition_with_bandage(self):
        """Test treating minor_cut with bandage."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            await add_condition(session, character, "minor_cut")
            # Set duration low so it gets removed
            character.conditions["minor_cut"]["duration"] = 1
            # Add bandage to inventory
            from app.services.character.inventory import add_item

            await add_item(session, character, "Bandage", 1, 10, "consumable")
            await session.commit()

            result = await treat_condition(session, character, "minor_cut", "bandage")
            assert (
                result["removed"] is True
            )  # minor_cut severity 1, reduced by 1, duration <= 2 -> removed
            assert result["treatment_used"] == "Bandage"
            assert "minor_cut" not in character.conditions

    @pytest.mark.asyncio
    async def test_treat_condition_reduces_severity(self):
        """Test treating deep_wound reduces severity but doesn't remove."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            await add_condition(session, character, "deep_wound")  # severity 2
            # Add bandage to inventory
            from app.services.character.inventory import add_item

            await add_item(session, character, "Bandage", 1, 10, "consumable")
            await session.commit()

            result = await treat_condition(session, character, "deep_wound", "bandage")
            assert result["removed"] is False
            assert result["old_severity"] == 2
            assert result["new_severity"] == 1
            assert character.conditions["deep_wound"]["severity"] == 1

    @pytest.mark.asyncio
    async def test_treat_wrong_condition_fails(self):
        """Test treating condition with wrong treatment fails."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            await add_condition(session, character, "poison")
            await session.commit()

            with pytest.raises(Exception) as exc_info:
                await treat_condition(session, character, "poison", "bandage")
            assert "cannot treat" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_treat_nonexistent_condition_fails(self):
        """Test treating nonexistent condition fails."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            with pytest.raises(Exception) as exc_info:
                await treat_condition(session, character, "minor_cut", "bandage")
            assert "Condition not found" in str(exc_info.value)


class TestInjuryGeneration:
    """Tests for injury generation from damage/exposure."""

    @pytest.mark.asyncio
    async def test_generate_injury_from_light_damage(self):
        """Test light damage (< 10) doesn't generate injuries."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            injuries = await generate_injury_from_damage(
                session, character, 5, rng_seed=123
            )
            assert len(injuries) == 0

    @pytest.mark.asyncio
    async def test_generate_injury_from_severe_damage(self):
        """Test severe damage (>= 30) has high chance of injury."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Use a seed that should trigger injury
            injuries = await generate_injury_from_damage(
                session, character, 35, rng_seed=1
            )
            # May or may not generate injury based on RNG
            for injury in injuries:
                assert injury in ["deep_wound", "broken_bone", "concussion", "burn"]

    @pytest.mark.asyncio
    async def test_generate_illness_from_cold_exposure(self):
        """Test cold exposure can generate frostbite or illness."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            illnesses = await generate_illness_from_exposure(
                session, character, "cold", rng_seed=1
            )
            for illness in illnesses:
                assert illness in ["frostbite", "minor_illness", "serious_illness"]

    @pytest.mark.asyncio
    async def test_generate_illness_from_poison_exposure(self):
        """Test poison exposure can generate poison condition."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            illnesses = await generate_illness_from_exposure(
                session, character, "poison", rng_seed=1
            )
            for illness in illnesses:
                assert illness == "poison"


class TestConditionDurationReduction:
    """Tests for condition duration reduction over time."""

    @pytest.mark.asyncio
    async def test_reduce_condition_duration(self):
        """Test reducing condition duration by 1 day."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            await add_condition(session, character, "minor_cut")  # duration 3
            await session.commit()

            expired = await reduce_condition_duration(session, character)
            assert len(expired) == 0
            assert character.conditions["minor_cut"]["duration"] == 2

    @pytest.mark.asyncio
    async def test_condition_expires_when_duration_reaches_zero(self):
        """Test condition is removed when duration reaches 0."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            await add_condition(session, character, "minor_cut")
            # Set duration to 1
            character.conditions["minor_cut"]["duration"] = 1
            await session.commit()

            expired = await reduce_condition_duration(session, character)
            assert "minor_cut" in expired
            assert "minor_cut" not in character.conditions

    @pytest.mark.asyncio
    async def test_severity_reduces_over_time(self):
        """Test condition severity reduces over time."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            await add_condition(
                session, character, "deep_wound"
            )  # severity 2, duration 7
            # Set duration to halfway
            character.conditions["deep_wound"]["duration"] = 3
            await session.commit()

            await reduce_condition_duration(session, character)
            assert character.conditions["deep_wound"]["severity"] == 1


class TestConditionAPI:
    """Tests for condition API endpoints."""

    @pytest.mark.asyncio
    async def test_get_conditions_endpoint(self):
        """Test getting conditions via API."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/conditions/",
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()
            assert "conditions" in data
            assert isinstance(data["conditions"], list)

    @pytest.mark.asyncio
    async def test_get_conditions_with_condition(self):
        """Test getting conditions when character has conditions."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        # Add condition directly
        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            await add_condition(session, character, "minor_cut")
            await session.commit()
            # Refresh to ensure we get the latest state
            await session.refresh(character)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/conditions/",
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data["conditions"]) == 1
            assert data["conditions"][0]["id"] == "minor_cut"
            assert data["conditions"][0]["name"] == "Minor Cut"

    @pytest.mark.asyncio
    async def test_get_condition_definitions(self):
        """Test getting all condition definitions."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/conditions/definitions")
            assert response.status_code == 200
            data = response.json()
            assert "conditions" in data
            assert len(data["conditions"]) == len(CONDITIONS)

    @pytest.mark.asyncio
    async def test_get_treatment_definitions(self):
        """Test getting all treatment definitions."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/conditions/treatments")
            assert response.status_code == 200
            data = response.json()
            assert "treatments" in data
            assert len(data["treatments"]) == len(await TREATMENTS())

    @pytest.mark.asyncio
    async def test_treat_condition_endpoint(self):
        """Test treating condition via API."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        # Add condition directly
        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            await add_condition(session, character, "minor_cut")
            # Set duration low so it gets removed - need to flag modified
            character.conditions["minor_cut"]["duration"] = 1
            # Add bandage to inventory
            from app.services.character.inventory import add_item

            await add_item(session, character, "Bandage", 1, 10, "consumable")
            from sqlalchemy.orm.attributes import flag_modified

            flag_modified(character, "conditions")
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/conditions/treat",
                json={"condition_id": "minor_cut", "treatment_id": "bandage"},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["removed"] is True
            assert data["treatment_used"] == "Bandage"

    @pytest.mark.asyncio
    async def test_treat_condition_endpoint_invalid(self):
        """Test treating condition with invalid treatment via API."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            await add_condition(session, character, "poison")
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/conditions/treat",
                json={"condition_id": "poison", "treatment_id": "bandage"},
                params={"session_token": session_token},
            )
            assert response.status_code == 400
            data = response.json()
            assert (
                "cannot treat" in data["detail"]["message"]
                or "Condition not found" in data["detail"]["message"]
            )


class TestConditionInducedDeath:
    """Tests for death caused by condition effects."""

    @pytest.mark.asyncio
    async def test_condition_effects_can_kill_character(self):
        """Test that condition effects can reduce health to zero and kill character."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Set health low
            character.current_health = 2
            character.max_health = 100
            # Add poison condition (-5 health per period)
            await add_condition(session, character, "poison")
            await session.commit()

            # Apply condition effects
            result = await apply_condition_effects(session, character)

            assert result["health_change"] == -2  # Clamped at 0
            assert result["died"] is True
            assert character.is_alive is False
            assert character.current_health == 0
            assert character.death_cause is not None

    @pytest.mark.asyncio
    async def test_condition_effects_health_bounds(self):
        """Test that health stays within valid bounds after condition effects."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = 1
            character.max_health = 100
            # Add serious illness (-3 health per period)
            await add_condition(session, character, "serious_illness")
            await session.commit()

            result = await apply_condition_effects(session, character)

            # Health should be clamped at 0, not go negative
            assert character.current_health == 0
            assert result["health_change"] == -1  # Actual change applied

    @pytest.mark.asyncio
    async def test_condition_death_persists(self):
        """Test that condition-induced death persists in database."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = 1
            character.max_health = 100
            await add_condition(session, character, "poison")  # -5 health
            await session.commit()

            await apply_condition_effects(session, character)
            await session.commit()

            # Refresh and check
            await session.refresh(character)
            assert character.is_alive is False
            assert character.current_health == 0

    @pytest.mark.asyncio
    async def test_condition_effects_died_flag_in_activity_response(self):
        """Test that activity responses include died flag when condition kills."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        # Set up character with low health and poison
        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = 1
            character.max_health = 100
            character.current_stamina = 100  # Enough for explore
            await add_condition(session, character, "poison")
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Explore should succeed (has stamina) but condition effects kill
            response = await client.post(
                "/api/activities/explore",
                json={},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()
            # Activity succeeded but condition effects killed
            assert data["result"]["died"] is True


class TestTreatmentAtomicity:
    """Tests for treatment transaction atomicity (item consumption + condition modification)."""

    @pytest.mark.asyncio
    async def test_treat_condition_atomicity_success(self):
        """Test that successful treatment atomically consumes item and modifies condition."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Add condition with severity 2
            await add_condition(
                session, character, "deep_wound"
            )  # severity 2, duration 7
            # Add bandage to inventory
            from app.services.character.inventory import add_item

            await add_item(session, character, "Bandage", 1, 10, "consumable")
            await session.commit()

            # Get initial state
            initial_bandage_count = await get_item_count(session, character, "bandage")
            initial_severity = character.conditions["deep_wound"]["severity"]

            # Treat condition
            from app.services.character.inventory import treat_condition_with_item

            result = await treat_condition_with_item(
                session, character, "deep_wound", "bandage"
            )
            await session.commit()

            # Verify atomic success: both item consumed AND condition modified
            assert result["success"] is True
            assert result["removed"] is False  # severity goes from 2->1, not removed
            assert result["old_severity"] == 2
            assert result["new_severity"] == 1
            assert result["item_consumed"]["fully_removed"] is True

            # Verify item was consumed
            final_bandage_count = await get_item_count(session, character, "bandage")
            assert final_bandage_count == initial_bandage_count - 1

            # Verify condition was modified
            assert (
                character.conditions["deep_wound"]["severity"] == initial_severity - 1
            )

    @pytest.mark.asyncio
    async def test_treat_condition_atomicity_item_not_in_inventory(self):
        """Test that treatment fails atomically when item not in inventory (no side effects)."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Add condition but NO bandage in inventory
            await add_condition(
                session, character, "minor_cut"
            )  # severity 1, duration 3
            await session.commit()

            # Get initial state
            initial_bandage_count = await get_item_count(session, character, "bandage")
            initial_severity = character.conditions["minor_cut"]["severity"]

            # Try to treat without item - should fail with ResourceError
            from app.services.character.inventory import treat_condition_with_item
            from app.core.exceptions import ResourceError

            with pytest.raises(ResourceError) as exc_info:
                await treat_condition_with_item(
                    session, character, "minor_cut", "bandage"
                )

            # Verify atomic failure: no item consumed, condition unchanged
            assert "don't have" in str(exc_info.value).lower()

            # Verify item was NOT consumed (was never there)
            final_bandage_count = await get_item_count(session, character, "bandage")
            assert final_bandage_count == initial_bandage_count

            # Verify condition was NOT modified
            assert character.conditions["minor_cut"]["severity"] == initial_severity

    @pytest.mark.asyncio
    async def test_treat_condition_atomicity_invalid_treatment(self):
        """Test that treatment fails atomically when treatment can't treat condition."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Add poison condition
            await add_condition(session, character, "poison")
            # Add bandage to inventory (but bandage can't treat poison)
            from app.services.character.inventory import add_item

            await add_item(session, character, "Bandage", 1, 10, "consumable")
            await session.commit()

            # Get initial state
            initial_bandage_count = await get_item_count(session, character, "bandage")
            initial_severity = character.conditions["poison"]["severity"]

            # Try to treat poison with bandage - should fail with ValidationError
            from app.services.character.inventory import treat_condition_with_item
            from app.core.exceptions import ValidationError

            with pytest.raises(ValidationError) as exc_info:
                await treat_condition_with_item(session, character, "poison", "bandage")

            # Verify atomic failure: item NOT consumed, condition unchanged
            assert "cannot treat" in str(exc_info.value).lower()

            final_bandage_count = await get_item_count(session, character, "bandage")
            assert final_bandage_count == initial_bandage_count

            assert character.conditions["poison"]["severity"] == initial_severity

    @pytest.mark.asyncio
    async def test_treat_condition_atomicity_condition_not_found(self):
        """Test that treatment fails atomically when condition doesn't exist."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Add bandage to inventory
            from app.services.character.inventory import add_item

            await add_item(session, character, "Bandage", 1, 10, "consumable")
            await session.commit()

            # Get initial state
            initial_bandage_count = await get_item_count(session, character, "bandage")

            # Try to treat non-existent condition
            from app.services.character.inventory import treat_condition_with_item
            from app.core.exceptions import ValidationError

            with pytest.raises(ValidationError) as exc_info:
                await treat_condition_with_item(
                    session, character, "nonexistent_condition", "bandage"
                )

            # Verify atomic failure: item NOT consumed
            assert "condition not found" in str(exc_info.value).lower()

            final_bandage_count = await get_item_count(session, character, "bandage")
            assert final_bandage_count == initial_bandage_count

    @pytest.mark.asyncio
    async def test_treat_condition_atomicity_full_removal(self):
        """Test atomicity when treatment fully removes condition (severity reaches 0)."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Add condition with severity 1 and low duration
            await add_condition(
                session, character, "minor_cut"
            )  # severity 1, duration 3
            # Set duration low so it gets fully removed
            character.conditions["minor_cut"]["duration"] = 1
            # Add bandage to inventory
            from app.services.character.inventory import add_item

            await add_item(session, character, "Bandage", 1, 10, "consumable")
            from sqlalchemy.orm.attributes import flag_modified

            flag_modified(character, "conditions")
            await session.commit()

            # Get initial state
            initial_bandage_count = await get_item_count(session, character, "bandage")

            # Treat condition - should fully remove it
            from app.services.character.inventory import treat_condition_with_item

            result = await treat_condition_with_item(
                session, character, "minor_cut", "bandage"
            )
            await session.commit()

            # Verify atomic success
            assert result["success"] is True
            assert result["removed"] is True
            assert result["new_severity"] == 0

            # Verify item consumed
            final_bandage_count = await get_item_count(session, character, "bandage")
            assert final_bandage_count == initial_bandage_count - 1

            # Verify condition fully removed
            assert "minor_cut" not in character.conditions

    @pytest.mark.asyncio
    async def test_treat_condition_atomicity_multiple_items(self):
        """Test atomicity with multiple items in inventory (only one consumed)."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Add condition
            await add_condition(session, character, "deep_wound")  # severity 2
            # Add multiple bandages
            from app.services.character.inventory import add_item

            await add_item(session, character, "Bandage", 3, 10, "consumable")
            await session.commit()

            # Get initial state
            initial_bandage_count = await get_item_count(session, character, "bandage")
            assert initial_bandage_count == 3

            # Treat condition - should consume only 1
            from app.services.character.inventory import treat_condition_with_item

            result = await treat_condition_with_item(
                session, character, "deep_wound", "bandage"
            )
            await session.commit()

            # Verify only 1 item consumed
            assert result["item_consumed"]["removed_quantity"] == 1
            assert result["item_consumed"]["fully_removed"] is False

            final_bandage_count = await get_item_count(session, character, "bandage")
            assert final_bandage_count == 2  # 3 - 1 = 2

            # Verify condition modified
            assert character.conditions["deep_wound"]["severity"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
