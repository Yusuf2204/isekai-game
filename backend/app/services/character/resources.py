"""Character resource management service.

Provides centralized validation and management of character resources
(health, stamina, fatigue, etc.) with consistent bounds checking and persistence.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceError
from app.models.gameplay import Character
from app.services.character.conditions import (
    calculate_total_penalties,
    get_effective_stamina,
    validate_health_bounds,
)


async def validate_stamina_bounds(character: Character) -> None:
    """Validate that character stamina is within valid bounds.

    Args:
        character: Character to validate

    Raises:
        ResourceError: If stamina is out of bounds
    """
    if character.current_stamina < 0:
        raise ResourceError(
            "Stamina cannot be negative",
            details={
                "current_stamina": character.current_stamina,
                "max_stamina": character.max_stamina,
            },
        )

    if character.current_stamina > character.max_stamina:
        raise ResourceError(
            "Stamina cannot exceed maximum",
            details={
                "current_stamina": character.current_stamina,
                "max_stamina": character.max_stamina,
            },
        )

    if character.max_stamina <= 0:
        raise ResourceError(
            "Maximum stamina must be positive",
            details={"max_stamina": character.max_stamina},
        )


async def validate_fatigue_bounds(character: Character) -> None:
    """Validate that character fatigue is within valid bounds.

    Args:
        character: Character to validate

    Raises:
        ResourceError: If fatigue is out of bounds
    """
    if character.fatigue_level < 0:
        raise ResourceError(
            "Fatigue cannot be negative",
            details={"fatigue_level": character.fatigue_level},
        )

    if character.fatigue_level > 10:
        raise ResourceError(
            "Fatigue level cannot exceed 10",
            details={"fatigue_level": character.fatigue_level},
        )


async def apply_health_change(
    session: AsyncSession,
    character: Character,
    amount: int,
) -> dict:
    """Apply a health change to a character with bounds validation.

    Args:
        session: Database session
        character: Character to modify
        amount: Health change (positive = heal, negative = damage)

    Returns:
        Dictionary with change details:
        - previous_health: int
        - new_health: int
        - max_health: int
        - change_amount: int (actual change applied after clamping)
        - was_clamped: bool (whether change was limited by bounds)

    Raises:
        ResourceError: If resulting health would be invalid
    """
    previous_health = character.current_health
    new_health = previous_health + amount

    # Clamp to valid range
    was_clamped = False
    if new_health < 0:
        new_health = 0
        was_clamped = True
    elif new_health > character.max_health:
        new_health = character.max_health
        was_clamped = True

    actual_change = new_health - previous_health
    character.current_health = new_health

    await session.flush()
    await validate_health_bounds(character)

    return {
        "previous_health": previous_health,
        "new_health": new_health,
        "max_health": character.max_health,
        "change_amount": actual_change,
        "was_clamped": was_clamped,
    }


async def apply_stamina_change(
    session: AsyncSession,
    character: Character,
    amount: int,
) -> dict:
    """Apply a stamina change to a character with bounds validation.

    Args:
        session: Database session
        character: Character to modify
        amount: Stamina change (positive = restore, negative = consume)

    Returns:
        Dictionary with change details:
        - previous_stamina: int
        - new_stamina: int
        - max_stamina: int
        - change_amount: int (actual change applied after clamping)
        - was_clamped: bool (whether change was limited by bounds)

    Raises:
        ResourceError: If resulting stamina would be invalid
    """
    previous_stamina = character.current_stamina
    new_stamina = previous_stamina + amount

    # Clamp to valid range
    was_clamped = False
    if new_stamina < 0:
        new_stamina = 0
        was_clamped = True
    elif new_stamina > character.max_stamina:
        new_stamina = character.max_stamina
        was_clamped = True

    actual_change = new_stamina - previous_stamina
    character.current_stamina = new_stamina

    await session.flush()
    await validate_stamina_bounds(character)

    return {
        "previous_stamina": previous_stamina,
        "new_stamina": new_stamina,
        "max_stamina": character.max_stamina,
        "change_amount": actual_change,
        "was_clamped": was_clamped,
    }


async def restore_stamina(
    session: AsyncSession,
    character: Character,
    amount: int,
) -> dict:
    """Restore stamina (positive change only).

    Args:
        session: Database session
        character: Character to restore stamina for
        amount: Amount to restore (must be positive)

    Returns:
        Dictionary with restore details (same as apply_stamina_change)
    """
    if amount <= 0:
        raise ResourceError(
            "Stamina restore amount must be positive",
            details={"amount": amount},
        )
    return await apply_stamina_change(session, character, amount)


async def consume_stamina(
    session: AsyncSession,
    character: Character,
    amount: int,
) -> dict:
    """Consume stamina (negative change only).

    Args:
        session: Database session
        character: Character to consume stamina from
        amount: Amount to consume (must be positive)

    Returns:
        Dictionary with consume details (same as apply_stamina_change)
    """
    if amount <= 0:
        raise ResourceError(
            "Stamina consume amount must be positive",
            details={"amount": amount},
        )
    return await apply_stamina_change(session, character, -amount)


async def heal_character(
    session: AsyncSession,
    character: Character,
    amount: int,
) -> dict:
    """Heal a character (positive health change only).

    Args:
        session: Database session
        character: Character to heal
        amount: Amount to heal (must be positive)

    Returns:
        Dictionary with heal details (same as apply_health_change)
    """
    if amount <= 0:
        raise ResourceError(
            "Heal amount must be positive",
            details={"amount": amount},
        )
    return await apply_health_change(session, character, amount)


async def damage_character(
    session: AsyncSession,
    character: Character,
    amount: int,
) -> dict:
    """Damage a character (negative health change only).

    Args:
        session: Database session
        character: Character to damage
        amount: Amount of damage (must be positive)

    Returns:
        Dictionary with damage details (same as apply_health_change)
    """
    if amount <= 0:
        raise ResourceError(
            "Damage amount must be positive",
            details={"amount": amount},
        )
    return await apply_health_change(session, character, -amount)


async def check_death(character: Character) -> bool:
    """Check if character has died (health at or below 0).

    Args:
        character: Character to check

    Returns:
        True if character is dead, False otherwise
    """
    return character.current_health <= 0


async def apply_fatigue_change(
    session: AsyncSession,
    character: Character,
    amount: int,
) -> dict:
    """Apply a fatigue change to a character with bounds validation.

    Args:
        session: Database session
        character: Character to modify
        amount: Fatigue change (positive = increase fatigue, negative = reduce)

    Returns:
        Dictionary with change details:
        - previous_fatigue: int
        - new_fatigue: int
        - change_amount: int (actual change applied after clamping)
        - was_clamped: bool (whether change was limited by bounds)

    Raises:
        ResourceError: If resulting fatigue would be invalid
    """
    previous_fatigue = character.fatigue_level
    new_fatigue = previous_fatigue + amount

    # Clamp to valid range (0-10)
    was_clamped = False
    if new_fatigue < 0:
        new_fatigue = 0
        was_clamped = True
    elif new_fatigue > 10:
        new_fatigue = 10
        was_clamped = True

    actual_change = new_fatigue - previous_fatigue
    character.fatigue_level = new_fatigue

    await session.flush()
    await validate_fatigue_bounds(character)

    return {
        "previous_fatigue": previous_fatigue,
        "new_fatigue": new_fatigue,
        "change_amount": actual_change,
        "was_clamped": was_clamped,
    }


async def increase_fatigue(
    session: AsyncSession,
    character: Character,
    amount: int,
) -> dict:
    """Increase fatigue (positive change only).

    Args:
        session: Database session
        character: Character to increase fatigue for
        amount: Amount to increase (must be positive)

    Returns:
        Dictionary with fatigue increase details
    """
    if amount <= 0:
        raise ResourceError(
            "Fatigue increase amount must be positive",
            details={"amount": amount},
        )
    return await apply_fatigue_change(session, character, amount)


async def reduce_fatigue(
    session: AsyncSession,
    character: Character,
    amount: int,
) -> dict:
    """Reduce fatigue (negative change only).

    Args:
        session: Database session
        character: Character to reduce fatigue for
        amount: Amount to reduce (must be positive)

    Returns:
        Dictionary with fatigue reduction details
    """
    if amount <= 0:
        raise ResourceError(
            "Fatigue reduction amount must be positive",
            details={"amount": amount},
        )
    return await apply_fatigue_change(session, character, -amount)


async def get_resource_status(character: Character) -> dict:
    """Get complete resource status for a character.

    Args:
        character: Character to get status for

    Returns:
        Dictionary with resource status
    """
    effective_max_stamina = await get_effective_stamina(character)
    penalties = await calculate_total_penalties(character)

    health_pct = (
        (character.current_health / character.max_health * 100)
        if character.max_health > 0
        else 0.0
    )
    health_pct = min(100.0, max(0.0, health_pct))

    stamina_pct = (
        (character.current_stamina / effective_max_stamina * 100)
        if effective_max_stamina > 0
        else 0.0
    )
    stamina_pct = min(100.0, max(0.0, stamina_pct))

    fatigue_pct = min(100.0, max(0.0, character.fatigue_level / 10 * 100))

    return {
        "health": {
            "current": character.current_health,
            "max": character.max_health,
            "percent": round(health_pct, 1),
        },
        "stamina": {
            "current": character.current_stamina,
            "max": character.max_stamina,
            "effective_max": effective_max_stamina,
            "percent": round(stamina_pct, 1),
        },
        "fatigue": {
            "level": character.fatigue_level,
            "max": 10,
            "percent": round(fatigue_pct, 1),
        },
        "is_alive": character.is_alive,
        "money": character.money,
        "penalties": {
            "stamina_penalty": penalties["stamina_penalty"],
            "attribute_penalties": penalties["attribute_penalties"],
        },
    }


async def validate_character_resources(character: Character) -> None:
    """Validate all character resources are in valid state.

    Args:
        character: Character to validate

    Raises:
        ResourceError: If any resource is invalid
    """
    await validate_health_bounds(character)
    await validate_stamina_bounds(character)
    await validate_fatigue_bounds(character)

    if character.money < 0:
        raise ResourceError(
            "Money cannot be negative",
            details={"money": character.money},
        )

    if character.level < 1:
        raise ResourceError(
            "Level must be at least 1",
            details={"level": character.level},
        )

    if character.experience < 0:
        raise ResourceError(
            "Experience cannot be negative",
            details={"experience": character.experience},
        )

    if character.attribute_points < 0:
        raise ResourceError(
            "Attribute points cannot be negative",
            details={"attribute_points": character.attribute_points},
        )
