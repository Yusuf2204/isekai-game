"""Character progression service: XP and level management."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.enums import AttributeName, SkillName
from app.models.gameplay import Character, CharacterAttribute, CharacterSkill


async def grant_character_xp(
    session: AsyncSession,
    character: Character,
    xp: int,
) -> dict:
    """
    Grant XP to a character and handle level-up.

    Args:
        session: Database session
        character: Character to grant XP to
        xp: Amount of XP to grant (must be positive)

    Returns:
        Dictionary with level-up info:
        - xp_granted: int
        - previous_level: int
        - new_level: int
        - leveled_up: bool
        - xp_remaining: int (XP after level-up)
        - xp_for_next_level: int
        - attribute_points_gained: int
    """
    if xp <= 0:
        return {
            "xp_granted": 0,
            "previous_level": character.level,
            "new_level": character.level,
            "leveled_up": False,
            "xp_remaining": character.experience,
            "xp_for_next_level": character.experience_for_next_level,
            "attribute_points_gained": 0,
        }

    previous_level = character.level
    character.experience += xp

    leveled_up = False
    attribute_points_gained = 0
    # Handle multiple level-ups if XP is enough
    while character.experience >= character.experience_for_next_level:
        character.experience -= character.experience_for_next_level
        character.level += 1
        leveled_up = True
        attribute_points_gained += 1

    # Award attribute points for level-ups
    if attribute_points_gained > 0:
        character.attribute_points += attribute_points_gained

    await session.flush()

    return {
        "xp_granted": xp,
        "previous_level": previous_level,
        "new_level": character.level,
        "leveled_up": leveled_up,
        "xp_remaining": character.experience,
        "xp_for_next_level": character.experience_for_next_level,
        "attribute_points_gained": attribute_points_gained,
    }


async def get_character_progression(character: Character) -> dict:
    """
    Get character progression status.

    Returns:
        Dictionary with progression info:
        - level: int
        - experience: int
        - experience_for_next_level: int
        - progress_percent: float (0-100)
    """
    xp_for_next = character.experience_for_next_level
    progress = (character.experience / xp_for_next * 100) if xp_for_next > 0 else 0

    return {
        "level": character.level,
        "experience": character.experience,
        "experience_for_next_level": xp_for_next,
        "progress_percent": round(progress, 1),
    }


async def grant_skill_xp(
    session: AsyncSession,
    character: Character,
    skill_name: str,
    xp: int,
) -> dict:
    """
    Grant XP to a skill and handle level-up.

    Args:
        session: Database session
        character: Character to grant skill XP to
        skill_name: Name of the skill (e.g., "survival", "trading")
        xp: Amount of XP to grant (must be positive)

    Returns:
        Dictionary with level-up info:
        - skill_name: str
        - xp_granted: int
        - previous_level: int
        - new_level: int
        - leveled_up: bool
        - xp_remaining: int (XP after level-up)
        - xp_for_next_level: int
    """
    try:
        skill_enum = SkillName(skill_name)
    except ValueError:
        return {
            "skill_name": skill_name,
            "xp_granted": 0,
            "previous_level": 0,
            "new_level": 0,
            "leveled_up": False,
            "xp_remaining": 0,
            "xp_for_next_level": 0,
        }

    if xp <= 0:
        # Still return current state
        result = await session.execute(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.name == skill_enum,
            )
        )
        skill = result.scalar_one_or_none()
        if skill:
            return {
                "skill_name": skill_name,
                "xp_granted": 0,
                "previous_level": skill.level,
                "new_level": skill.level,
                "leveled_up": False,
                "xp_remaining": skill.experience,
                "xp_for_next_level": skill.experience_for_next_level,
            }
        return {
            "skill_name": skill_name,
            "xp_granted": 0,
            "previous_level": 0,
            "new_level": 0,
            "leveled_up": False,
            "xp_remaining": 0,
            "xp_for_next_level": 50,  # level 0 * 100 + 50
        }

    result = await session.execute(
        select(CharacterSkill).where(
            CharacterSkill.character_id == character.id,
            CharacterSkill.name == skill_enum,
        )
    )
    skill = result.scalar_one_or_none()

    if skill:
        previous_level = skill.level
        skill.experience += xp

        leveled_up = False
        # Handle multiple level-ups if XP is enough
        while skill.experience >= skill.experience_for_next_level:
            skill.experience -= skill.experience_for_next_level
            skill.level += 1
            leveled_up = True
    else:
        # Create new skill at level 0 with XP
        previous_level = 0
        skill = CharacterSkill(
            character_id=character.id,
            name=skill_enum,
            level=0,
            experience=xp,
        )
        session.add(skill)
        await session.flush()

        leveled_up = False
        # Handle multiple level-ups if XP is enough
        while skill.experience >= skill.experience_for_next_level:
            skill.experience -= skill.experience_for_next_level
            skill.level += 1
            leveled_up = True

    await session.flush()

    return {
        "skill_name": skill_name,
        "xp_granted": xp,
        "previous_level": previous_level,
        "new_level": skill.level,
        "leveled_up": leveled_up,
        "xp_remaining": skill.experience,
        "xp_for_next_level": skill.experience_for_next_level,
    }


def get_skill_progression_from_skill(skill: CharacterSkill | None) -> dict:
    """
    Get skill progression status from a skill object.

    Returns:
        Dictionary with progression info:
        - name: str
        - level: int
        - experience: int
        - experience_for_next_level: int
        - progress_percent: float (0-100)
    """
    if skill is None:
        return {
            "name": "",
            "level": 0,
            "experience": 0,
            "experience_for_next_level": 50,
            "progress_percent": 0.0,
        }

    xp_for_next = skill.experience_for_next_level
    progress = (skill.experience / xp_for_next * 100) if xp_for_next > 0 else 0

    return {
        "name": skill.name.value,
        "level": skill.level,
        "experience": skill.experience,
        "experience_for_next_level": xp_for_next,
        "progress_percent": round(progress, 1),
    }


# =============================================================================
# Attribute Development Service
# =============================================================================

MAX_ATTRIBUTE_VALUE = 30  # Reasonable cap for attribute values


async def get_attribute_points(character: Character) -> dict:
    """
    Get the character's current unspent attribute points.

    Returns:
        Dictionary with:
        - attribute_points: int (unspent points)
    """
    return {
        "attribute_points": character.attribute_points,
    }


async def allocate_attribute_points(
    session: AsyncSession,
    character: Character,
    attribute_name: str,
    points: int = 1,
) -> dict:
    """
    Allocate attribute points to a character attribute.

    Args:
        session: Database session
        character: Character to allocate points to
        attribute_name: Name of the attribute (e.g., "strength", "agility")
        points: Number of points to allocate (must be positive)

    Returns:
        Dictionary with allocation result:
        - attribute_name: str
        - points_allocated: int
        - previous_value: int
        - new_value: int
        - remaining_points: int

    Raises:
        ValidationError: If allocation is invalid
    """
    # Validate points
    if points <= 0:
        raise ValidationError(
            "Points to allocate must be positive",
            details={"points": points, "attribute_name": attribute_name},
        )

    # Check if character has enough points
    if character.attribute_points < points:
        raise ValidationError(
            "Insufficient attribute points",
            details={
                "available_points": character.attribute_points,
                "requested_points": points,
                "attribute_name": attribute_name,
            },
        )

    # Validate attribute name
    try:
        attr_enum = AttributeName(attribute_name)
    except ValueError:
        raise ValidationError(
            "Invalid attribute name",
            details={
                "attribute_name": attribute_name,
                "valid_attributes": [a.value for a in AttributeName],
            },
        )

    # Get the character's attribute
    result = await session.execute(
        select(CharacterAttribute).where(
            CharacterAttribute.character_id == character.id,
            CharacterAttribute.name == attr_enum,
        )
    )
    attribute = result.scalar_one_or_none()

    if attribute is None:
        raise ValidationError(
            "Character attribute not found",
            details={"attribute_name": attribute_name},
        )

    # Check attribute cap
    if attribute.current_value + points > MAX_ATTRIBUTE_VALUE:
        raise ValidationError(
            f"Attribute would exceed maximum value of {MAX_ATTRIBUTE_VALUE}",
            details={
                "attribute_name": attribute_name,
                "current_value": attribute.current_value,
                "requested_points": points,
                "max_value": MAX_ATTRIBUTE_VALUE,
            },
        )

    previous_value = attribute.current_value
    attribute.current_value += points
    character.attribute_points -= points

    await session.flush()

    return {
        "attribute_name": attribute_name,
        "points_allocated": points,
        "previous_value": previous_value,
        "new_value": attribute.current_value,
        "remaining_points": character.attribute_points,
    }


async def get_character_attributes(character: Character) -> list[dict]:
    """
    Get all character attributes with progression info.

    Returns:
        List of dictionaries with attribute info
    """
    result = []
    for attr in character.attributes:
        result.append(
            {
                "name": attr.name.value,
                "base_value": attr.base_value,
                "current_value": attr.current_value,
                "experience": attr.experience,
            }
        )
    return result


# =============================================================================
# Unified Progression Status Service
# =============================================================================


async def get_unified_progression_status(
    session: AsyncSession,
    character: Character,
) -> dict:
    """
    Get complete unified progression status for a character.

    Returns:
        Dictionary with:
        - character: level, experience, experience_for_next_level, progress_percent, attribute_points
        - skills: list of all skills with progression (level, experience, experience_for_next_level, progress_percent)
        - attributes: list of all attributes with values (base_value, current_value, experience)
    """
    from app.models.gameplay import CharacterSkill, CharacterAttribute

    # Character progression
    char_progression = await get_character_progression(character)

    # Get all skills for this character
    skills_result = await session.execute(
        select(CharacterSkill).where(CharacterSkill.character_id == character.id)
    )
    skills = skills_result.scalars().all()

    skill_progressions = []
    for skill in skills:
        skill_progressions.append(get_skill_progression_from_skill(skill))

    # Get all attributes for this character
    attrs_result = await session.execute(
        select(CharacterAttribute).where(
            CharacterAttribute.character_id == character.id
        )
    )
    attributes = attrs_result.scalars().all()

    attribute_progressions = []
    for attr in attributes:
        attribute_progressions.append(
            {
                "name": attr.name.value,
                "base_value": attr.base_value,
                "current_value": attr.current_value,
                "experience": attr.experience,
            }
        )

    return {
        "character": {
            "level": char_progression["level"],
            "experience": char_progression["experience"],
            "experience_for_next_level": char_progression["experience_for_next_level"],
            "progress_percent": char_progression["progress_percent"],
            "attribute_points": character.attribute_points,
        },
        "skills": skill_progressions,
        "attributes": attribute_progressions,
    }
