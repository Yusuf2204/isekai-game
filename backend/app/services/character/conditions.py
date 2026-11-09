"""Character conditions service.

Manages injuries, sickness, and other conditions affecting characters.
"""

from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.exceptions import ResourceError, ValidationError
from app.core.rng import get_rng
from app.models.enums import DeathCause
from app.models.gameplay import Character
from app.services.character.inventory import (
    treat_condition_with_item,
    get_treatment_definition,
    get_all_treatments,
)


def validate_health_bounds(character: Character) -> None:
    """Validate that character health is within valid bounds.

    Args:
        character: Character to validate

    Raises:
        ResourceError: If health is out of bounds
    """
    if character.current_health < 0:
        raise ResourceError(
            "Health cannot be negative",
            details={
                "current_health": character.current_health,
                "max_health": character.max_health,
            },
        )

    if character.current_health > character.max_health:
        raise ResourceError(
            "Health cannot exceed maximum",
            details={
                "current_health": character.current_health,
                "max_health": character.max_health,
            },
        )

    if character.max_health <= 0:
        raise ResourceError(
            "Maximum health must be positive",
            details={"max_health": character.max_health},
        )


# Condition definitions
CONDITIONS = {
    "minor_cut": {
        "name": "Minor Cut",
        "description": "A small wound that stings but isn't serious.",
        "base_severity": 1,
        "max_duration": 3,
        "health_per_period": -1,
        "stamina_penalty": 0,
        "attribute_penalties": {},
    },
    "deep_wound": {
        "name": "Deep Wound",
        "description": "A serious wound that bleeds and hampers movement.",
        "base_severity": 2,
        "max_duration": 7,
        "health_per_period": -2,
        "stamina_penalty": 10,
        "attribute_penalties": {"agility": -2, "strength": -1},
    },
    "broken_bone": {
        "name": "Broken Bone",
        "description": "A fractured limb that severely limits mobility.",
        "base_severity": 3,
        "max_duration": 14,
        "health_per_period": -1,
        "stamina_penalty": 25,
        "attribute_penalties": {"agility": -4, "strength": -3},
    },
    "concussion": {
        "name": "Concussion",
        "description": "Head trauma causing confusion and nausea.",
        "base_severity": 2,
        "max_duration": 5,
        "health_per_period": 0,
        "stamina_penalty": 15,
        "attribute_penalties": {"intelligence": -3, "agility": -2},
    },
    "minor_illness": {
        "name": "Minor Illness",
        "description": "A mild fever and fatigue.",
        "base_severity": 1,
        "max_duration": 4,
        "health_per_period": -1,
        "stamina_penalty": 10,
        "attribute_penalties": {"vitality": -1, "strength": -1},
    },
    "serious_illness": {
        "name": "Serious Illness",
        "description": "High fever, chills, and severe weakness.",
        "base_severity": 2,
        "max_duration": 10,
        "health_per_period": -3,
        "stamina_penalty": 30,
        "attribute_penalties": {
            "vitality": -3,
            "strength": -2,
            "agility": -2,
            "intelligence": -1,
        },
    },
    "poison": {
        "name": "Poison",
        "description": "Toxin coursing through your veins.",
        "base_severity": 2,
        "max_duration": 3,
        "health_per_period": -5,
        "stamina_penalty": 20,
        "attribute_penalties": {"vitality": -2, "agility": -2},
    },
    "burn": {
        "name": "Burn",
        "description": "Seared flesh that hurts with every movement.",
        "base_severity": 2,
        "max_duration": 7,
        "health_per_period": -2,
        "stamina_penalty": 15,
        "attribute_penalties": {"agility": -2, "strength": -1},
    },
    "frostbite": {
        "name": "Frostbite",
        "description": "Numb, damaged tissue from extreme cold.",
        "base_severity": 2,
        "max_duration": 10,
        "health_per_period": -1,
        "stamina_penalty": 15,
        "attribute_penalties": {"agility": -3, "vitality": -2},
    },
    "exhaustion": {
        "name": "Exhaustion",
        "description": "Complete physical and mental drain.",
        "base_severity": 1,
        "max_duration": 2,
        "health_per_period": 0,
        "stamina_penalty": 40,
        "attribute_penalties": {"strength": -2, "agility": -2, "intelligence": -2},
    },
}

class ConditionError(ValidationError):
    """Condition-specific error."""

    pass


async def get_condition_definition(condition_id: str) -> dict | None:
    """Get condition definition by ID."""
    return CONDITIONS.get(condition_id)


async def get_all_conditions() -> dict:
    """Get all condition definitions."""
    return CONDITIONS.copy()


async def add_condition(
    session: AsyncSession,
    character: Character,
    condition_id: str,
    severity: int | None = None,
    duration: int | None = None,
) -> dict:
    """Add a condition to a character.

    Args:
        session: Database session
        character: Character to add condition to
        condition_id: ID of the condition
        severity: Optional severity override (1-3)
        duration: Optional duration override in days

    Returns:
        Dictionary with condition details
    """
    definition = CONDITIONS.get(condition_id)
    if not definition:
        raise ConditionError(
            f"Unknown condition: {condition_id}",
            details={"condition_id": condition_id},
        )

    # Initialize conditions dict if needed
    if character.conditions is None:
        character.conditions = {}

    # Determine severity and duration
    cond_severity = severity or definition["base_severity"]
    cond_duration = duration or definition["max_duration"]

    # Check if condition already exists
    if condition_id in character.conditions:
        # Worsen existing condition
        existing = character.conditions[condition_id]
        existing["severity"] = min(3, existing["severity"] + 1)
        existing["duration"] = max(existing["duration"], cond_duration)
        existing["description"] = definition["description"]
    else:
        # Add new condition
        character.conditions[condition_id] = {
            "name": definition["name"],
            "description": definition["description"],
            "severity": cond_severity,
            "duration": cond_duration,
            "max_duration": definition["max_duration"],
            "health_per_period": definition["health_per_period"],
            "stamina_penalty": definition["stamina_penalty"],
            "attribute_penalties": definition["attribute_penalties"],
        }

    flag_modified(character, "conditions")
    await session.flush()
    return character.conditions[condition_id]


async def remove_condition(
    session: AsyncSession,
    character: Character,
    condition_id: str,
) -> bool:
    """Remove a condition from a character.

    Returns:
        True if condition was removed, False if not found
    """
    if character.conditions and condition_id in character.conditions:
        del character.conditions[condition_id]
        flag_modified(character, "conditions")
        await session.flush()
        return True
    return False


async def reduce_condition_duration(
    session: AsyncSession,
    character: Character,
) -> list[str]:
    """Reduce duration of all conditions by 1 (called each day).

    Returns:
        List of condition IDs that expired
    """
    expired = []
    if not character.conditions:
        return expired

    to_remove = []
    for cond_id, cond in character.conditions.items():
        cond["duration"] -= 1
        if cond["duration"] <= 0:
            to_remove.append(cond_id)
        # Also reduce severity over time for healing conditions
        elif (
            cond["severity"] > 1
            and cond["duration"] <= cond.get("max_duration", 1) // 2
        ):
            cond["severity"] = max(1, cond["severity"] - 1)

    for cond_id in to_remove:
        del character.conditions[cond_id]
        expired.append(cond_id)

    if to_remove or any(
        cond["duration"] != cond.get("max_duration", 0)
        for cond in character.conditions.values()
    ):
        flag_modified(character, "conditions")
        await session.flush()

    return expired


async def apply_condition_effects(
    session: AsyncSession,
    character: Character,
) -> dict:
    """Apply periodic effects of all conditions (health loss, etc.).

    Returns:
        Dictionary with total health change, stamina penalty, attribute penalties,
        and death status
    """
    total_health_change = 0
    total_stamina_penalty = 0
    total_attribute_penalties: dict[str, int] = {}

    if not character.conditions:
        return {
            "health_change": 0,
            "stamina_penalty": 0,
            "attribute_penalties": {},
            "died": False,
        }

    for cond_id, cond in character.conditions.items():
        total_health_change += cond.get("health_per_period", 0)
        total_stamina_penalty += cond.get("stamina_penalty", 0)
        for attr, penalty in cond.get("attribute_penalties", {}).items():
            total_attribute_penalties[attr] = (
                total_attribute_penalties.get(attr, 0) + penalty
            )

    # Apply health change
    died = False
    if total_health_change != 0:
        from app.services.character.resources import apply_health_change, check_death

        result = await apply_health_change(session, character, total_health_change)
        total_health_change = result["change_amount"]

        # Check if character died from condition effects
        if await check_death(character):
            died = True
            character.is_alive = False
            character.died_at = datetime.now(timezone.utc)
            character.death_cause = DeathCause.ILLNESS
            character.death_description = "Succumbed to injuries and illness"
            character.age_at_death = character.age

    return {
        "health_change": total_health_change,
        "stamina_penalty": total_stamina_penalty,
        "attribute_penalties": total_attribute_penalties,
        "died": died,
    }


async def treat_condition(
    session: AsyncSession,
    character: Character,
    condition_id: str,
    treatment_id: str,
) -> dict:
    """Treat a condition with a treatment item from inventory.

    This delegates to the inventory service which handles atomic item consumption
    and condition treatment.

    Args:
        session: Database session
        character: Character being treated
        condition_id: Condition to treat
        treatment_id: Treatment to use

    Returns:
        Dictionary with treatment result
    """
    from app.services.character.inventory import treat_condition_with_item

    return await treat_condition_with_item(
        session=session,
        character=character,
        condition_id=condition_id,
        treatment_id=treatment_id,
    )


async def get_character_conditions(character: Character) -> list[dict]:
    """Get all conditions for a character with full details."""
    if not character.conditions:
        return []

    conditions = []
    for cond_id, cond in character.conditions.items():
        conditions.append(
            {
                "id": cond_id,
                "name": cond["name"],
                "description": cond["description"],
                "severity": cond["severity"],
                "duration": cond["duration"],
                "max_duration": cond.get("max_duration", 0),
                "stamina_penalty": cond.get("stamina_penalty", 0),
                "attribute_penalties": cond.get("attribute_penalties", {}),
                "health_per_period": cond.get("health_per_period", 0),
            }
        )
    return conditions


async def calculate_total_penalties(character: Character) -> dict:
    """Calculate total penalties from all conditions and fatigue."""
    total_stamina_penalty = 0
    total_attribute_penalties: dict[str, int] = {}

    # Condition penalties
    if character.conditions:
        for cond in character.conditions.values():
            total_stamina_penalty += cond.get("stamina_penalty", 0)
            for attr, penalty in cond.get("attribute_penalties", {}).items():
                total_attribute_penalties[attr] = (
                    total_attribute_penalties.get(attr, 0) + penalty
                )

    # Fatigue penalties
    if character.fatigue_level > 0:
        # Each level of fatigue reduces effective stamina and attributes
        total_stamina_penalty += character.fatigue_level * 5
        for attr in ["strength", "agility", "intelligence", "vitality"]:
            total_attribute_penalties[attr] = (
                total_attribute_penalties.get(attr, 0) - character.fatigue_level
            )

    return {
        "stamina_penalty": total_stamina_penalty,
        "attribute_penalties": total_attribute_penalties,
    }


async def get_effective_stamina(character: Character) -> int:
    """Get character's effective max stamina after penalties."""
    penalties = await calculate_total_penalties(character)
    effective_max = character.max_stamina - penalties["stamina_penalty"]
    return max(1, effective_max)


async def get_effective_attribute(
    character: Character,
    attribute_name: str,
    base_value: int,
) -> int:
    """Get character's effective attribute value after penalties."""
    penalties = await calculate_total_penalties(character)
    penalty = penalties["attribute_penalties"].get(attribute_name, 0)
    return max(1, base_value + penalty)


async def generate_injury_from_damage(
    session: AsyncSession,
    character: Character,
    damage_amount: int,
    rng_seed: int | None = None,
) -> list[str]:
    """Generate injuries based on damage taken.

    Args:
        session: Database session
        character: Character taking damage
        damage_amount: Amount of damage taken
        rng_seed: Optional RNG seed

    Returns:
        List of condition IDs added
    """
    rng = get_rng(rng_seed or character.session_id)

    # Threshold for injury chance
    if damage_amount < 10:
        return []  # Minor damage doesn't cause injuries

    injuries_added = []

    # Chance based on damage severity
    if damage_amount >= 30:
        # Severe damage - high chance of serious injury
        possible_injuries = ["deep_wound", "broken_bone", "concussion", "burn"]
        injury_chance = 0.5
    elif damage_amount >= 20:
        # Moderate damage
        possible_injuries = ["deep_wound", "minor_cut", "concussion", "burn"]
        injury_chance = 0.3
    else:
        # Light damage
        possible_injuries = ["minor_cut", "burn"]
        injury_chance = 0.15

    if rng.random() < injury_chance:
        injury = rng.choice(possible_injuries)
        await add_condition(session, character, injury)
        injuries_added.append(injury)

    return injuries_added


async def generate_illness_from_exposure(
    session: AsyncSession,
    character: Character,
    exposure_type: str,
    rng_seed: int | None = None,
) -> list[str]:
    """Generate illness from environmental exposure.

    Args:
        session: Database session
        character: Character exposed
        exposure_type: Type of exposure (cold, heat, poison, disease)
        rng_seed: Optional RNG seed

    Returns:
        List of condition IDs added
    """
    rng = get_rng(rng_seed or character.session_id)

    exposure_illnesses = {
        "cold": ["frostbite", "minor_illness", "serious_illness"],
        "heat": ["minor_illness", "exhaustion"],
        "poison": ["poison"],
        "disease": ["minor_illness", "serious_illness"],
    }

    possible = exposure_illnesses.get(exposure_type, ["minor_illness"])
    chance = {"cold": 0.2, "heat": 0.15, "poison": 0.3, "disease": 0.25}.get(
        exposure_type, 0.1
    )

    if rng.random() < chance:
        illness = rng.choice(possible)
        await add_condition(session, character, illness)
        return [illness]

    return []


if __name__ == "__main__":
    # Quick test
    import asyncio

    async def test():
        print("Conditions module loaded successfully")
        print(f"Available conditions: {list(CONDITIONS.keys())}")
        print(f"Available treatments: {list(TREATMENTS.keys())}")

    asyncio.run(test())
