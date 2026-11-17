"""Stage 4 regression tests for resource and condition mathematics."""

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_session, recreate_db
from app.core.exceptions import ValidationError
from app.models.enums import (
    ActivityType,
    BackgroundName,
    GenderPresentation,
    RaceName,
    TimeOfDay,
)
from app.models.gameplay import Character, GameplayState
from app.services.character.conditions import (
    ConditionError,
    add_condition,
    get_effective_stamina,
    validate_health_bounds as condition_validate_health_bounds,
)
from app.services.character.creation import create_character
from app.services.character.resources import (
    get_resource_status,
    validate_health_bounds as resource_validate_health_bounds,
)
from app.services.game.activities import (
    _validate_stamina_for_activity,
    perform_explore,
    perform_rest,
)
from app.services.world import seed_world


@pytest_asyncio.fixture
async def prepared_database() -> None:
    """Recreate and seed the test database for a Stage 4 test."""
    await recreate_db()
    async with get_session() as session:
        await seed_world(session)


async def _create_character() -> tuple[int, int, str]:
    """Helper to create a test character and return (character_id, session_id, session_token)."""
    async with get_session() as session:
        character, game_session = await create_character(
            session=session,
            name="Stage 4 Hero",
            race_name=RaceName.HUMAN,
            background_name=BackgroundName.COMMONER,
            gender_presentation=GenderPresentation.MALE,
        )
        return (character.id, game_session.id, game_session.session_token)


async def _get_character_loaded(session, character_id: int) -> Character:
    """Helper to get character with all relations loaded."""
    result = await session.execute(
        select(Character)
        .where(Character.id == character_id)
        .options(
            selectinload(Character.attributes),
            selectinload(Character.skills),
        )
    )
    character = result.scalar_one_or_none()
    assert character is not None
    return character


# ---------------------------------------------------------------------------
# CB-10: Interrupted rest health calculation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_interrupted_rest_health_change_matches_actual_change(
    prepared_database,
) -> None:
    """Interrupted rest must not subtract health loss twice in reported health_change."""
    character_id, session_id, _ = await _create_character()

    async with get_session() as session:
        character = await _get_character_loaded(session, character_id)
        gameplay_state = await session.scalar(
            select(GameplayState).where(GameplayState.session_id == session_id)
        )
        assert gameplay_state is not None

        # Set character to damaged health, evening, location with danger
        character.current_health = 50
        character.max_health = 100
        gameplay_state.current_time_of_day = TimeOfDay.EVENING

        initial_health = character.current_health

        # We force an interrupted rest using a seed that triggers interruption
        # Or test perform_rest directly
        # Seed 31 with evening danger level triggers interruption check (health_loss=3)
        rest_result = await perform_rest(
            session=session,
            character=character,
            gameplay_state=gameplay_state,
            duration="long",
            rng_seed=31,
        )

        assert rest_result["was_interrupted"] is True
        actual_health_diff = character.current_health - initial_health
        reported_health_change = rest_result["result"]["health_change"]

        # If interrupted, reported change must still match the actual health delta
        assert reported_health_change == actual_health_diff


# ---------------------------------------------------------------------------
# CB-11: Consolidate duplicate health-bound validators
# ---------------------------------------------------------------------------


def test_validate_health_bounds_is_single_shared_function() -> None:
    """condition_validate_health_bounds should be the same function as resource_validate_health_bounds."""
    assert condition_validate_health_bounds is resource_validate_health_bounds


# ---------------------------------------------------------------------------
# CB-13: Severity and duration handling (including 0 values and negative validation)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_condition_severity_zero_override(prepared_database) -> None:
    """severity=0 must be respected as an explicit override and not fallback to base_severity."""
    character_id, _, _ = await _create_character()

    async with get_session() as session:
        character = await session.get(Character, character_id)
        assert character is not None

        result = await add_condition(
            session=session,
            character=character,
            condition_id="minor_cut",
            severity=0,
        )

        assert result["severity"] == 0


@pytest.mark.asyncio
async def test_condition_duration_zero_override(prepared_database) -> None:
    """duration=0 must be respected as an explicit override and not fallback to max_duration."""
    character_id, _, _ = await _create_character()

    async with get_session() as session:
        character = await session.get(Character, character_id)
        assert character is not None

        result = await add_condition(
            session=session,
            character=character,
            condition_id="minor_cut",
            duration=0,
        )

        assert result["duration"] == 0


@pytest.mark.asyncio
async def test_condition_negative_severity_rejected(prepared_database) -> None:
    """Negative severity must raise ConditionError/ValidationError."""
    character_id, _, _ = await _create_character()

    async with get_session() as session:
        character = await session.get(Character, character_id)
        assert character is not None

        with pytest.raises((ConditionError, ValidationError)):
            await add_condition(
                session=session,
                character=character,
                condition_id="minor_cut",
                severity=-1,
            )


@pytest.mark.asyncio
async def test_condition_negative_duration_rejected(prepared_database) -> None:
    """Negative duration must raise ConditionError/ValidationError."""
    character_id, _, _ = await _create_character()

    async with get_session() as session:
        character = await session.get(Character, character_id)
        assert character is not None

        with pytest.raises((ConditionError, ValidationError)):
            await add_condition(
                session=session,
                character=character,
                condition_id="minor_cut",
                duration=-1,
            )


# ---------------------------------------------------------------------------
# CB-14: Stamina percentage clamping (0 - 100)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stamina_percent_clamped_at_100(prepared_database) -> None:
    """Stamina percentage in get_character_resources must never exceed 100%."""
    character_id, _, _ = await _create_character()

    async with get_session() as session:
        character = await session.get(Character, character_id)
        assert character is not None

        # Give character full stamina (100)
        character.current_stamina = 100
        character.max_stamina = 100

        # Add condition with stamina penalty (e.g. deep_wound has stamina_penalty = 10)
        await add_condition(session, character, "deep_wound")

        effective_max = await get_effective_stamina(character)
        assert effective_max == 90  # 100 - 10

        resources = await get_resource_status(character)
        # Without clamp, 100 / 90 * 100 would be 111.1%
        assert resources["stamina"]["percent"] <= 100.0
        assert resources["stamina"]["percent"] == 100.0


# ---------------------------------------------------------------------------
# CB-15: Activity stamina validation respects effective stamina
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_activity_validation_rejects_when_effective_stamina_insufficient(
    prepared_database,
) -> None:
    """Activity validation must reject when penalties reduce effective stamina below requirement."""
    character_id, _, _ = await _create_character()

    async with get_session() as session:
        character = await session.get(Character, character_id)
        assert character is not None

        # Explore requires 15 stamina.
        # Character has current_stamina = 15, max_stamina = 20.
        character.current_stamina = 15
        character.max_stamina = 20
        character.fatigue_level = 0

        # deep_wound has stamina_penalty = 10
        await add_condition(session, character, "deep_wound")
        effective_max = await get_effective_stamina(character)
        assert effective_max == 10  # 20 - 10

        # Current stamina is 15, but effective stamina limit is 10. Required is 15.
        with pytest.raises(ValidationError) as exc_info:
            await _validate_stamina_for_activity(character, ActivityType.EXPLORE)

        assert "Insufficient stamina" in str(exc_info.value.message)


# ---------------------------------------------------------------------------
# PR-10: RNG seed fallback (0 is not treated as falsy)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_activity_rng_seed_zero_is_deterministic(prepared_database) -> None:
    """Passing rng_seed=0 must use seed 0 and not fall back to session_id."""
    character_id, session_id, _ = await _create_character()

    async with get_session() as session:
        character = await _get_character_loaded(session, character_id)
        gameplay_state = await session.scalar(
            select(GameplayState).where(GameplayState.session_id == session_id)
        )
        assert gameplay_state is not None

        # Two explore runs with rng_seed=0 must produce identical outcome
        character.current_stamina = 100
        result1 = await perform_explore(
            session=session,
            character=character,
            gameplay_state=gameplay_state,
            rng_seed=0,
        )

        character.current_stamina = 100
        result2 = await perform_explore(
            session=session,
            character=character,
            gameplay_state=gameplay_state,
            rng_seed=0,
        )

        assert result1["result"]["health_change"] == result2["result"]["health_change"]
        assert result1["result"]["money_change"] == result2["result"]["money_change"]
        assert result1["result"]["items_gained"] == result2["result"]["items_gained"]
