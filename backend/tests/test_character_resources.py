"""Tests for character resource foundation."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.core.database import get_session, recreate_db
from app.models.enums import RaceName, BackgroundName, GenderPresentation
from app.models.gameplay import Character, GameplayState
from app.services.world import seed_world
from app.services.character.creation import create_character
from app.services.character.resources import (
    validate_health_bounds,
    validate_stamina_bounds,
    validate_fatigue_bounds,
    apply_health_change,
    apply_stamina_change,
    heal_character,
    damage_character,
    restore_stamina,
    consume_stamina,
    apply_fatigue_change,
    increase_fatigue,
    reduce_fatigue,
    check_death,
    get_resource_status,
    validate_character_resources,
    ResourceError,
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


class TestResourceService:
    """Tests for resource service functions."""

    @pytest.mark.asyncio
    async def test_validate_health_bounds_valid(self):
        """Test health validation with valid values."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Should not raise
            await validate_health_bounds(character)

    @pytest.mark.asyncio
    async def test_validate_health_bounds_negative_current(self):
        """Test health validation fails with negative current health."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = -5
            with pytest.raises(ResourceError) as exc_info:
                await validate_health_bounds(character)
            assert "negative" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_health_bounds_exceeds_max(self):
        """Test health validation fails when current exceeds max."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = 150
            character.max_health = 100
            with pytest.raises(ResourceError) as exc_info:
                await validate_health_bounds(character)
            assert "exceed maximum" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_health_bounds_zero_max(self):
        """Test health validation fails with zero max health."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = 0
            character.max_health = 0
            with pytest.raises(ResourceError) as exc_info:
                await validate_health_bounds(character)
            assert "positive" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_apply_health_change_heal(self):
        """Test applying positive health change (heal)."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Damage first
            character.current_health = 50
            await session.flush()

            result = await apply_health_change(session, character, 30)

            assert result["previous_health"] == 50
            assert result["new_health"] == 80
            assert result["change_amount"] == 30
            assert result["was_clamped"] is False

    @pytest.mark.asyncio
    async def test_apply_health_change_damage(self):
        """Test applying negative health change (damage)."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = 80
            await session.flush()

            result = await apply_health_change(session, character, -30)

            assert result["previous_health"] == 80
            assert result["new_health"] == 50
            assert result["change_amount"] == -30
            assert result["was_clamped"] is False

    @pytest.mark.asyncio
    async def test_apply_health_change_clamped_at_max(self):
        """Test heal clamped at max health."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = 90
            character.max_health = 100
            await session.flush()

            result = await apply_health_change(session, character, 30)

            assert result["previous_health"] == 90
            assert result["new_health"] == 100
            assert result["change_amount"] == 10
            assert result["was_clamped"] is True

    @pytest.mark.asyncio
    async def test_apply_health_change_clamped_at_zero(self):
        """Test damage clamped at zero health."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = 20
            await session.flush()

            result = await apply_health_change(session, character, -50)

            assert result["previous_health"] == 20
            assert result["new_health"] == 0
            assert result["change_amount"] == -20
            assert result["was_clamped"] is True

    @pytest.mark.asyncio
    async def test_heal_character_valid(self):
        """Test heal_character with valid amount."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = 50
            await session.flush()

            result = await heal_character(session, character, 25)

            assert result["new_health"] == 75
            assert result["change_amount"] == 25

    @pytest.mark.asyncio
    async def test_heal_character_invalid_amount(self):
        """Test heal_character rejects non-positive amount."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            with pytest.raises(ResourceError) as exc_info:
                await heal_character(session, character, 0)
            assert "positive" in str(exc_info.value)

            with pytest.raises(ResourceError):
                await heal_character(session, character, -10)

    @pytest.mark.asyncio
    async def test_damage_character_valid(self):
        """Test damage_character with valid amount."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = 80
            await session.flush()

            result = await damage_character(session, character, 25)

            assert result["new_health"] == 55
            assert result["change_amount"] == -25

    @pytest.mark.asyncio
    async def test_damage_character_invalid_amount(self):
        """Test damage_character rejects non-positive amount."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            with pytest.raises(ResourceError):
                await damage_character(session, character, 0)
            with pytest.raises(ResourceError):
                await damage_character(session, character, -10)

    @pytest.mark.asyncio
    async def test_check_death_alive(self):
        """Test check_death returns False for alive character."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = 50
            assert await check_death(character) is False

    @pytest.mark.asyncio
    async def test_check_death_at_zero(self):
        """Test check_death returns True at zero health."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = 0
            assert await check_death(character) is True

    @pytest.mark.asyncio
    async def test_check_death_below_zero(self):
        """Test check_death returns True below zero health."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = -5
            assert await check_death(character) is True

    @pytest.mark.asyncio
    async def test_get_resource_status(self):
        """Test get_resource_status returns correct structure."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = 75
            character.max_health = 100
            character.money = 500
            await session.flush()

            result = await get_resource_status(character)

            assert result["health"]["current"] == 75
            assert result["health"]["max"] == 100
            assert result["health"]["percent"] == 75.0
            assert result["is_alive"] is True
            assert result["money"] == 500

    @pytest.mark.asyncio
    async def test_get_resource_status_zero_max(self):
        """Test get_resource_status handles zero max health."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = 0
            character.max_health = 0
            await session.flush()

            result = await get_resource_status(character)

            assert result["health"]["current"] == 0
            assert result["health"]["max"] == 0
            assert result["health"]["percent"] == 0.0

    @pytest.mark.asyncio
    async def test_validate_character_resources_valid(self):
        """Test validate_character_resources passes for valid character."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Should not raise
            await validate_character_resources(character)

    @pytest.mark.asyncio
    async def test_validate_character_resources_negative_money(self):
        """Test validate_character_resources fails with negative money."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.money = -100
            with pytest.raises(ResourceError) as exc_info:
                await validate_character_resources(character)
            assert "negative" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_character_resources_invalid_level(self):
        """Test validate_character_resources fails with invalid level."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.level = 0
            with pytest.raises(ResourceError) as exc_info:
                await validate_character_resources(character)
            assert "at least 1" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_character_resources_negative_xp(self):
        """Test validate_character_resources fails with negative experience."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.experience = -50
            with pytest.raises(ResourceError) as exc_info:
                await validate_character_resources(character)
            assert "negative" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_character_resources_negative_attribute_points(self):
        """Test validate_character_resources fails with negative attribute points."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.attribute_points = -1
            with pytest.raises(ResourceError) as exc_info:
                await validate_character_resources(character)
            assert "negative" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_stamina_bounds_valid(self):
        """Test stamina validation with valid values."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Should not raise
            await validate_stamina_bounds(character)

    @pytest.mark.asyncio
    async def test_validate_stamina_bounds_negative_current(self):
        """Test stamina validation fails with negative current stamina."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_stamina = -5
            with pytest.raises(ResourceError) as exc_info:
                await validate_stamina_bounds(character)
            assert "negative" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_stamina_bounds_exceeds_max(self):
        """Test stamina validation fails when current exceeds max."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_stamina = 150
            character.max_stamina = 100
            with pytest.raises(ResourceError) as exc_info:
                await validate_stamina_bounds(character)
            assert "exceed maximum" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_fatigue_bounds_valid(self):
        """Test fatigue validation with valid values."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            # Should not raise for values 0-10
            for i in range(11):
                character.fatigue_level = i
                await validate_fatigue_bounds(character)

    @pytest.mark.asyncio
    async def test_validate_fatigue_bounds_negative(self):
        """Test fatigue validation fails with negative fatigue."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.fatigue_level = -1
            with pytest.raises(ResourceError) as exc_info:
                await validate_fatigue_bounds(character)
            assert "negative" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_fatigue_bounds_exceeds_max(self):
        """Test fatigue validation fails when fatigue exceeds 10."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.fatigue_level = 11
            with pytest.raises(ResourceError) as exc_info:
                await validate_fatigue_bounds(character)
            assert "exceed 10" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_apply_stamina_change_restore(self):
        """Test applying positive stamina change (restore)."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_stamina = 50
            await session.flush()

            result = await apply_stamina_change(session, character, 30)

            assert result["previous_stamina"] == 50
            assert result["new_stamina"] == 80
            assert result["change_amount"] == 30
            assert result["was_clamped"] is False

    @pytest.mark.asyncio
    async def test_apply_stamina_change_consume(self):
        """Test applying negative stamina change (consume)."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_stamina = 80
            await session.flush()

            result = await apply_stamina_change(session, character, -30)

            assert result["previous_stamina"] == 80
            assert result["new_stamina"] == 50
            assert result["change_amount"] == -30
            assert result["was_clamped"] is False

    @pytest.mark.asyncio
    async def test_apply_stamina_change_clamped_at_max(self):
        """Test stamina restore clamped at max stamina."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_stamina = 90
            character.max_stamina = 100
            await session.flush()

            result = await apply_stamina_change(session, character, 30)

            assert result["previous_stamina"] == 90
            assert result["new_stamina"] == 100
            assert result["change_amount"] == 10
            assert result["was_clamped"] is True

    @pytest.mark.asyncio
    async def test_apply_stamina_change_clamped_at_zero(self):
        """Test stamina consume clamped at zero."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_stamina = 20
            await session.flush()

            result = await apply_stamina_change(session, character, -50)

            assert result["previous_stamina"] == 20
            assert result["new_stamina"] == 0
            assert result["change_amount"] == -20
            assert result["was_clamped"] is True

    @pytest.mark.asyncio
    async def test_restore_stamina_valid(self):
        """Test restore_stamina with valid amount."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_stamina = 50
            await session.flush()

            result = await restore_stamina(session, character, 25)

            assert result["new_stamina"] == 75
            assert result["change_amount"] == 25

    @pytest.mark.asyncio
    async def test_restore_stamina_invalid_amount(self):
        """Test restore_stamina rejects non-positive amount."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            with pytest.raises(ResourceError) as exc_info:
                await restore_stamina(session, character, 0)
            assert "positive" in str(exc_info.value)

            with pytest.raises(ResourceError):
                await restore_stamina(session, character, -10)

    @pytest.mark.asyncio
    async def test_consume_stamina_valid(self):
        """Test consume_stamina with valid amount."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_stamina = 80
            await session.flush()

            result = await consume_stamina(session, character, 25)

            assert result["new_stamina"] == 55
            assert result["change_amount"] == -25

    @pytest.mark.asyncio
    async def test_consume_stamina_invalid_amount(self):
        """Test consume_stamina rejects non-positive amount."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            with pytest.raises(ResourceError):
                await consume_stamina(session, character, 0)
            with pytest.raises(ResourceError):
                await consume_stamina(session, character, -10)

    @pytest.mark.asyncio
    async def test_apply_fatigue_change_increase(self):
        """Test applying positive fatigue change (increase)."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.fatigue_level = 2
            await session.flush()

            result = await apply_fatigue_change(session, character, 3)

            assert result["previous_fatigue"] == 2
            assert result["new_fatigue"] == 5
            assert result["change_amount"] == 3
            assert result["was_clamped"] is False

    @pytest.mark.asyncio
    async def test_apply_fatigue_change_reduce(self):
        """Test applying negative fatigue change (reduce)."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.fatigue_level = 5
            await session.flush()

            result = await apply_fatigue_change(session, character, -3)

            assert result["previous_fatigue"] == 5
            assert result["new_fatigue"] == 2
            assert result["change_amount"] == -3
            assert result["was_clamped"] is False

    @pytest.mark.asyncio
    async def test_apply_fatigue_change_clamped_at_zero(self):
        """Test fatigue reduction clamped at zero."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.fatigue_level = 2
            await session.flush()

            result = await apply_fatigue_change(session, character, -5)

            assert result["previous_fatigue"] == 2
            assert result["new_fatigue"] == 0
            assert result["change_amount"] == -2
            assert result["was_clamped"] is True

    @pytest.mark.asyncio
    async def test_apply_fatigue_change_clamped_at_max(self):
        """Test fatigue increase clamped at 10."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.fatigue_level = 8
            await session.flush()

            result = await apply_fatigue_change(session, character, 5)

            assert result["previous_fatigue"] == 8
            assert result["new_fatigue"] == 10
            assert result["change_amount"] == 2
            assert result["was_clamped"] is True

    @pytest.mark.asyncio
    async def test_increase_fatigue_valid(self):
        """Test increase_fatigue with valid amount."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.fatigue_level = 2
            await session.flush()

            result = await increase_fatigue(session, character, 3)

            assert result["new_fatigue"] == 5
            assert result["change_amount"] == 3

    @pytest.mark.asyncio
    async def test_increase_fatigue_invalid_amount(self):
        """Test increase_fatigue rejects non-positive amount."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            with pytest.raises(ResourceError) as exc_info:
                await increase_fatigue(session, character, 0)
            assert "positive" in str(exc_info.value)

            with pytest.raises(ResourceError):
                await increase_fatigue(session, character, -10)

    @pytest.mark.asyncio
    async def test_reduce_fatigue_valid(self):
        """Test reduce_fatigue with valid amount."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.fatigue_level = 5
            await session.flush()

            result = await reduce_fatigue(session, character, 3)

            assert result["new_fatigue"] == 2
            assert result["change_amount"] == -3

    @pytest.mark.asyncio
    async def test_reduce_fatigue_invalid_amount(self):
        """Test reduce_fatigue rejects non-positive amount."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            with pytest.raises(ResourceError) as exc_info:
                await reduce_fatigue(session, character, 0)
            assert "positive" in str(exc_info.value)

            with pytest.raises(ResourceError):
                await reduce_fatigue(session, character, -10)

    @pytest.mark.asyncio
    async def test_get_resource_status_includes_stamina_fatigue(self):
        """Test get_resource_status returns stamina and fatigue info."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = 75
            character.max_health = 100
            character.current_stamina = 80
            character.max_stamina = 100
            character.fatigue_level = 2
            character.money = 500
            await session.flush()

            result = await get_resource_status(character)

            # Health
            assert result["health"]["current"] == 75
            assert result["health"]["max"] == 100
            assert result["health"]["percent"] == 75.0

            # Stamina
            assert "stamina" in result
            assert result["stamina"]["current"] == 80
            assert result["stamina"]["max"] == 100
            assert "effective_max" in result["stamina"]
            assert "percent" in result["stamina"]

            # Fatigue
            assert "fatigue" in result
            assert result["fatigue"]["level"] == 2
            assert result["fatigue"]["max"] == 10
            assert result["fatigue"]["percent"] == 20.0

            # Penalties
            assert "penalties" in result
            assert "stamina_penalty" in result["penalties"]
            assert "attribute_penalties" in result["penalties"]

            assert result["is_alive"] is True
            assert result["money"] == 500

    @pytest.mark.asyncio
    async def test_validate_character_resources_includes_stamina_fatigue(self):
        """Test validate_character_resources validates stamina and fatigue."""
        await _setup_db()
        character, game_session = await _create_character_with_session()

        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_stamina = -1
            with pytest.raises(ResourceError) as exc_info:
                await validate_character_resources(character)
            assert "negative" in str(exc_info.value)

            character.current_stamina = 50
            character.fatigue_level = 11
            with pytest.raises(ResourceError) as exc_info:
                await validate_character_resources(character)
            assert "exceed 10" in str(exc_info.value)


class TestResourceStatusEndpoint:
    """Tests for resource status API endpoint."""

    @pytest.mark.asyncio
    async def test_get_resource_status_endpoint(self):
        """Test getting resource status via API."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/character/resources",
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            assert "health" in data
            assert "stamina" in data
            assert "fatigue" in data
            assert "is_alive" in data
            assert "money" in data
            assert "penalties" in data

            health = data["health"]
            assert health["current"] == character.current_health
            assert health["max"] == character.max_health
            assert "percent" in health

            stamina = data["stamina"]
            assert stamina["current"] == character.current_stamina
            assert stamina["max"] == character.max_stamina
            assert "effective_max" in stamina
            assert "percent" in stamina

            fatigue = data["fatigue"]
            assert fatigue["level"] == character.fatigue_level
            assert fatigue["max"] == 10
            assert "percent" in fatigue

            assert data["is_alive"] is True
            assert data["money"] == character.money

    @pytest.mark.asyncio
    async def test_resource_status_reflects_damage(self):
        """Test resource status reflects damage from rest interruption."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Damage character directly in DB
            async with get_session() as session:
                character = await _get_character_in_session(session, character.id)
                character.current_health = 30
                await session.commit()

            response = await client.get(
                "/api/character/resources",
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            assert data["health"]["current"] == 30
            assert data["health"]["max"] == character.max_health
            assert data["health"]["percent"] == round(
                30 / character.max_health * 100, 1
            )

            # Stamina and fatigue should also be present
            assert "stamina" in data
            assert "fatigue" in data

    @pytest.mark.asyncio
    async def test_resource_status_persists(self):
        """Test resource status persists after simulated browser refresh."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        # First client
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Damage character
            async with get_session() as session:
                character = await _get_character_in_session(session, character.id)
                character.current_health = 40
                await session.commit()

            response = await client.get(
                "/api/character/resources",
                params={"session_token": session_token},
            )
            data1 = response.json()

        # Second client (simulated refresh)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client2:
            response = await client2.get(
                "/api/character/resources",
                params={"session_token": session_token},
            )
            data2 = response.json()

        assert data1["health"]["current"] == data2["health"]["current"]
        assert data1["health"]["max"] == data2["health"]["max"]
        assert data1["money"] == data2["money"]
        assert data1["stamina"]["current"] == data2["stamina"]["current"]
        assert data1["stamina"]["max"] == data2["stamina"]["max"]
        assert data1["fatigue"]["level"] == data2["fatigue"]["level"]

    @pytest.mark.asyncio
    async def test_invalid_session_token(self):
        """Test resource status endpoint with invalid session token."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/character/resources",
                params={"session_token": "invalid_token"},
            )
            assert response.status_code == 404
            data = response.json()
            assert data["detail"]["error"] == "NOT_FOUND"


class TestResourceIntegration:
    """Integration tests for resource system with existing activities."""

    @pytest.mark.asyncio
    async def test_rest_heals_health(self):
        """Test that rest activity properly heals health."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        # Damage character first
        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_health = 50
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Short rest
            response = await client.post(
                "/api/activities/rest",
                json={"duration": "short"},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            # Health should have increased
            assert data["result"]["health_change"] > 0
            # Stamina should have increased
            assert data["result"]["stamina_change"] > 0
            # Fatigue should have decreased
            assert data["result"]["fatigue_change"] < 0

            # Check resource status
            response = await client.get(
                "/api/character/resources",
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            resource_data = response.json()
            assert resource_data["health"]["current"] > 50

    @pytest.mark.asyncio
    async def test_explore_consumes_stamina_increases_fatigue(self):
        """Test that explore consumes stamina and increases fatigue."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/activities/explore",
                json={},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            # Explore consumes stamina
            assert data["result"]["stamina_change"] < 0
            # Explore increases fatigue
            assert data["result"]["fatigue_change"] > 0

            # Check resource status
            response = await client.get(
                "/api/character/resources",
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            resource_data = response.json()
            assert resource_data["stamina"]["current"] < character.max_stamina
            assert resource_data["fatigue"]["level"] > 0

    @pytest.mark.asyncio
    async def test_work_consumes_stamina_increases_fatigue(self):
        """Test that work consumes stamina and increases fatigue."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/activities/work",
                json={},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            # Work consumes stamina
            assert data["result"]["stamina_change"] < 0
            # Work increases fatigue
            assert data["result"]["fatigue_change"] > 0

            # Resource status accessible
            response = await client.get(
                "/api/character/resources",
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            resource_data = response.json()
            assert resource_data["stamina"]["current"] < character.max_stamina
            assert resource_data["fatigue"]["level"] > 0

    @pytest.mark.asyncio
    async def test_long_rest_restores_stamina_reduces_fatigue(self):
        """Test that long rest restores stamina and reduces fatigue more."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        # First, do some work to increase fatigue and consume stamina
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.post(
                "/api/activities/work",
                json={},
                params={"session_token": session_token},
            )

            # Now long rest
            response = await client.post(
                "/api/activities/rest",
                json={"duration": "long"},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            # Long rest restores more stamina
            assert data["result"]["stamina_change"] > 15
            # Long rest reduces fatigue more
            assert data["result"]["fatigue_change"] < -1


class TestStaminaPrerequisiteValidation:
    """Tests for stamina prerequisite validation in activities."""

    @pytest.mark.asyncio
    async def test_explore_rejected_when_insufficient_stamina(self):
        """Test explore is rejected when character has insufficient stamina."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        # Set stamina to 10 (less than 15 required for explore)
        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_stamina = 10
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/activities/explore",
                json={},
                params={"session_token": session_token},
            )
            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["error"] == "VALIDATION_ERROR"
            assert "Insufficient stamina" in data["detail"]["message"]

            # Verify no state changes
            response = await client.get(
                "/api/character/resources",
                params={"session_token": session_token},
            )
            resource_data = response.json()
            assert resource_data["stamina"]["current"] == 10  # Unchanged
            assert resource_data["fatigue"]["level"] == 0  # Unchanged

    @pytest.mark.asyncio
    async def test_work_rejected_when_insufficient_stamina(self):
        """Test work is rejected when character has insufficient stamina."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        # Set stamina to 15 (less than 20 required for work)
        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_stamina = 15
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/activities/work",
                json={},
                params={"session_token": session_token},
            )
            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["error"] == "VALIDATION_ERROR"
            assert "Insufficient stamina" in data["detail"]["message"]

            # Verify no state changes
            response = await client.get(
                "/api/character/resources",
                params={"session_token": session_token},
            )
            resource_data = response.json()
            assert resource_data["stamina"]["current"] == 15  # Unchanged
            assert resource_data["fatigue"]["level"] == 0  # Unchanged
            assert resource_data["money"] == character.money  # Unchanged

    @pytest.mark.asyncio
    async def test_explore_allowed_at_exact_stamina_threshold(self):
        """Test explore is allowed when character has exactly enough stamina."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        # Set stamina to exactly 15 (required for explore)
        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_stamina = 15
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/activities/explore",
                json={},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["result"]["success"] is True

            # Stamina should be consumed
            assert data["result"]["stamina_change"] == -15

    @pytest.mark.asyncio
    async def test_work_allowed_at_exact_stamina_threshold(self):
        """Test work is allowed when character has exactly enough stamina."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        # Set stamina to exactly 20 (required for work)
        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_stamina = 20
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/activities/work",
                json={},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["result"]["success"] is True

            # Stamina should be consumed
            assert data["result"]["stamina_change"] == -20

    @pytest.mark.asyncio
    async def test_rest_allowed_at_zero_stamina(self):
        """Test rest is allowed even when character has zero stamina."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        # Set stamina to 0
        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_stamina = 0
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/activities/rest",
                json={"duration": "short"},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["result"]["success"] is True

            # Stamina should be restored
            assert data["result"]["stamina_change"] > 0

    @pytest.mark.asyncio
    async def test_insufficient_stamina_no_time_advancement(self):
        """Test that time does not advance when activity is rejected for insufficient stamina."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        # Set stamina to 0
        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_stamina = 0
            # Get initial gameplay state
            result = await session.execute(
                select(GameplayState).where(GameplayState.session_id == game_session.id)
            )
            gameplay_state = result.scalar_one()
            initial_day = gameplay_state.current_day
            initial_time = gameplay_state.current_time_of_day
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/activities/explore",
                json={},
                params={"session_token": session_token},
            )
            assert response.status_code == 400

            # Check time hasn't advanced
            async with get_session() as session:
                result = await session.execute(
                    select(GameplayState).where(
                        GameplayState.session_id == game_session.id
                    )
                )
                gameplay_state = result.scalar_one()
                assert gameplay_state.current_day == initial_day
                assert gameplay_state.current_time_of_day == initial_time

    @pytest.mark.asyncio
    async def test_insufficient_stamina_no_rewards_granted(self):
        """Test that no XP, money, or items are granted when rejected for insufficient stamina."""
        await _setup_db()
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        # Set stamina to 0
        async with get_session() as session:
            character = await _get_character_in_session(session, character.id)
            character.current_stamina = 0
            initial_money = character.money
            initial_xp = character.experience
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/activities/work",
                json={},
                params={"session_token": session_token},
            )
            assert response.status_code == 400

            # Check resources unchanged
            response = await client.get(
                "/api/character/resources",
                params={"session_token": session_token},
            )
            resource_data = response.json()
            assert resource_data["money"] == initial_money

            # Check character XP unchanged
            async with get_session() as session:
                character = await _get_character_in_session(session, character.id)
                assert character.experience == initial_xp


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
