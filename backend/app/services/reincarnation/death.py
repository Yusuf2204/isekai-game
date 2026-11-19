"""Authoritative death recording, soul record creation, and legacy generation service."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.core.rng import SeededRNG
from app.models.enums import DeathCause, LegacyType
from app.models.gameplay import (
    Character,
    CharacterLegacy,
    GameplayState,
    GameSession,
    LifeRecord,
)


def compute_achievements(
    character: Character,
    days_lived: int,
    final_skills: dict[str, int],
    final_relationships: dict[str, int],
) -> list[str]:
    """Compute achievements earned during the character's life."""
    achievements: list[str] = ["Eldorian Citizen"]

    if days_lived >= 7:
        achievements.append("Survivor of the First Week")
    if days_lived >= 30:
        achievements.append("Seasoned Wanderer")
    if days_lived >= 100:
        achievements.append("Long-Lived Mortal")

    if character.money >= 100:
        achievements.append("Prosperous Citizen")
    if character.money >= 300:
        achievements.append("Wealthy Merchant")

    if character.level >= 3:
        achievements.append("Ascendant Adventurer")

    swordsmanship = final_skills.get("swordsmanship", 0)
    if swordsmanship >= 3:
        achievements.append("Blade Apprentice")
    if swordsmanship >= 5:
        achievements.append("Swordmaster")

    magic = final_skills.get("magic", 0)
    if magic >= 3:
        achievements.append("Acolyte of Arcana")

    herbalism = final_skills.get("herbalism", 0)
    if herbalism >= 3:
        achievements.append("Forest Apothecary")

    speech = final_skills.get("speech", 0)
    if speech >= 3:
        achievements.append("Silver-Tongued Diplomat")

    survival = final_skills.get("survival", 0)
    if survival >= 3:
        achievements.append("Wilderness Pathfinder")

    crafting = final_skills.get("crafting", 0)
    if crafting >= 3:
        achievements.append("Artisan Craftsman")

    if character.reputation >= 20:
        achievements.append("Celebrated Hero")
    elif character.reputation <= -20:
        achievements.append("Infamous Outlaw")

    if any(val >= 30 for val in final_relationships.values()):
        achievements.append("Beloved Companion")
    if any(val <= -30 for val in final_relationships.values()):
        achievements.append("Bitter Rival")

    return achievements


def generate_character_legacy(
    character: Character,
    session_seed: int,
    generation: int,
    final_attributes: dict[str, int],
    final_skills: dict[str, int],
) -> CharacterLegacy:
    """
    Generate a limited legacy from the deceased character.

    Adheres strictly to AGENTS.md §14 Recommendation 6:
    Max 1 legacy trait per life: +1 attribute, or skill affinity, or minor bonus.
    """
    rng = SeededRNG(session_seed + generation * 1047 + 73)

    # Determine highest attribute
    top_attr = "vitality"
    if final_attributes:
        top_attr = max(final_attributes.items(), key=lambda item: item[1])[0]

    # Determine highest skill
    top_skill = "survival"
    if final_skills:
        top_skill = max(final_skills.items(), key=lambda item: item[1])[0]

    # Pick 1 of 5 legacy archetypes
    flavor_roll = rng.choice([0, 1, 2, 3, 4])

    if flavor_roll == 0:
        # Attribute bonus
        return CharacterLegacy(
            character_id=character.id,
            legacy_type=LegacyType.ATTRIBUTE_BONUS,
            description=f"Ancestral vigor endures across reincarnations: +1 bonus to {top_attr.capitalize()}.",
            attribute_bonus=top_attr,
            attribute_bonus_value=1,
            skill_affinity=None,
            skill_affinity_bonus=0,
            memory_fragment=None,
            recurring_dream=None,
        )
    elif flavor_roll == 1:
        # Skill affinity
        return CharacterLegacy(
            character_id=character.id,
            legacy_type=LegacyType.SKILL_AFFINITY,
            description=f"Faint muscle memory from a past life awakens: +1 affinity in {top_skill.capitalize()}.",
            attribute_bonus=None,
            attribute_bonus_value=0,
            skill_affinity=top_skill,
            skill_affinity_bonus=1,
            memory_fragment=None,
            recurring_dream=None,
        )
    elif flavor_roll == 2:
        # Fragmented memory
        return CharacterLegacy(
            character_id=character.id,
            legacy_type=LegacyType.FRAGMENTED_MEMORY,
            description="Fragmented memories of Eldoria's ancient paths awaken in your subconscious mind.",
            attribute_bonus="luck",
            attribute_bonus_value=1,
            skill_affinity=None,
            skill_affinity_bonus=0,
            memory_fragment=f"Glimpses of {character.name}'s past triumphs and tragedies flicker in quiet moments.",
            recurring_dream=None,
        )
    elif flavor_roll == 3:
        # Recurring dream
        return CharacterLegacy(
            character_id=character.id,
            legacy_type=LegacyType.RECURRING_DREAM,
            description="A recurring dream of past struggles hardens your spirit against hardship.",
            attribute_bonus="vitality",
            attribute_bonus_value=1,
            skill_affinity=None,
            skill_affinity_bonus=0,
            memory_fragment=None,
            recurring_dream=f"You dream of {character.death_cause.value if character.death_cause else 'destiny'}, awakening with resolute endurance.",
        )
    else:
        # Inherited bonus
        return CharacterLegacy(
            character_id=character.id,
            legacy_type=LegacyType.INHERITED_BONUS,
            description="An ancestral keepsake and faint blessing passed down through blood and soul.",
            attribute_bonus="luck",
            attribute_bonus_value=1,
            skill_affinity=None,
            skill_affinity_bonus=0,
            memory_fragment=None,
            recurring_dream=None,
        )


async def record_death(
    session: AsyncSession,
    character_id: int,
    cause: DeathCause,
    death_description: str | None = None,
) -> tuple[Character, LifeRecord, CharacterLegacy]:
    """
    Authoritatively record a character's death, generate their LifeRecord, and create their CharacterLegacy.

    Idempotent: if a life record already exists for this character, returns existing records.
    """
    result = await session.execute(
        select(Character)
        .where(Character.id == character_id)
        .options(
            selectinload(Character.attributes),
            selectinload(Character.skills),
            selectinload(Character.inventory),
            selectinload(Character.npc_relationships),
        )
    )
    character = result.scalar_one_or_none()
    if character is None:
        raise NotFoundError("Character", str(character_id))

    # Check for existing LifeRecord
    existing_record_res = await session.execute(
        select(LifeRecord).where(LifeRecord.character_id == character.id)
    )
    existing_record = existing_record_res.scalar_one_or_none()
    if existing_record is not None:
        existing_legacy_res = await session.execute(
            select(CharacterLegacy).where(CharacterLegacy.character_id == character.id)
        )
        existing_legacy = existing_legacy_res.scalar_one_or_none()
        if existing_legacy is None:
            # Generate missing legacy if needed
            existing_legacy = generate_character_legacy(
                character=character,
                session_seed=42,
                generation=character.generation,
                final_attributes=existing_record.final_attributes,
                final_skills=existing_record.final_skills,
            )
            session.add(existing_legacy)
            await session.flush()
        return character, existing_record, existing_legacy

    # Load session and gameplay state
    session_res = await session.execute(
        select(GameSession).where(GameSession.id == character.session_id)
    )
    game_session = session_res.scalar_one_or_none()

    gp_res = await session.execute(
        select(GameplayState).where(GameplayState.character_id == character.id)
    )
    gameplay_state = gp_res.scalar_one_or_none()

    # Update character death info
    character.is_alive = False
    character.died_at = datetime.now(timezone.utc)
    character.death_cause = cause
    character.death_description = death_description or (
        f"Perished due to {cause.value.replace('_', ' ')}."
    )
    character.age_at_death = character.age

    # Days lived
    days_lived = max(1, gameplay_state.current_day) if gameplay_state else 1

    # Reset ongoing combat and active events on gameplay_state
    if gameplay_state:
        gameplay_state.in_combat = False
        gameplay_state.combat_state = {}
        gameplay_state.active_event_id = None
        gameplay_state.event_choices = []

    # Compile final snapshots
    final_attributes = {
        attr.name.value
        if hasattr(attr.name, "value")
        else str(attr.name): attr.current_value
        for attr in character.attributes
    }
    final_skills = {
        skill.name.value
        if hasattr(skill.name, "value")
        else str(skill.name): skill.level
        for skill in character.skills
    }
    final_money = character.money
    final_inventory = [
        {
            "item_id": item.item_id,
            "name": item.name,
            "quantity": item.quantity,
            "item_type": item.item_type,
            "properties": item.properties or {},
        }
        for item in character.inventory
    ]
    final_relationships = {
        str(rel.npc_id): rel.value for rel in character.npc_relationships
    }
    important_decisions = (
        list(gameplay_state.recent_activities) if gameplay_state else []
    )
    achievements = compute_achievements(
        character=character,
        days_lived=days_lived,
        final_skills=final_skills,
        final_relationships=final_relationships,
    )

    # Create LifeRecord
    life_record = LifeRecord(
        session_id=character.session_id,
        character_id=character.id,
        generation=character.generation,
        name=character.name,
        race_name=character.race_name,
        background_name=character.background_name,
        gender_presentation=character.gender_presentation,
        age_at_death=character.age,
        cause_of_death=cause,
        death_description=character.death_description,
        days_lived=days_lived,
        final_attributes=final_attributes,
        final_skills=final_skills,
        final_money=final_money,
        final_inventory=final_inventory,
        final_relationships=final_relationships,
        important_decisions=important_decisions,
        achievements=achievements,
    )
    session.add(life_record)

    # Generate CharacterLegacy
    legacy = generate_character_legacy(
        character=character,
        session_seed=game_session.seed if game_session else 42,
        generation=character.generation,
        final_attributes=final_attributes,
        final_skills=final_skills,
    )
    session.add(legacy)

    # Update session aggregate metrics
    if game_session:
        game_session.total_deaths += 1
        game_session.total_time_lived += days_lived

    await session.flush()
    await session.refresh(life_record)
    await session.refresh(legacy)

    return character, life_record, legacy


async def get_life_record_by_character(
    session: AsyncSession, character_id: int
) -> LifeRecord | None:
    """Retrieve the LifeRecord for a character."""
    result = await session.execute(
        select(LifeRecord).where(LifeRecord.character_id == character_id)
    )
    return result.scalar_one_or_none()


async def get_legacy_by_character(
    session: AsyncSession, character_id: int
) -> CharacterLegacy | None:
    """Retrieve the CharacterLegacy created by a character."""
    result = await session.execute(
        select(CharacterLegacy).where(CharacterLegacy.character_id == character_id)
    )
    return result.scalar_one_or_none()


async def get_session_life_records(
    session: AsyncSession, session_token: str
) -> list[LifeRecord]:
    """Retrieve all LifeRecords belonging to a game session ordered by generation."""
    session_res = await session.execute(
        select(GameSession).where(GameSession.session_token == session_token)
    )
    game_session = session_res.scalar_one_or_none()
    if game_session is None:
        raise NotFoundError("GameSession", session_token)

    result = await session.execute(
        select(LifeRecord)
        .where(LifeRecord.session_id == game_session.id)
        .order_by(LifeRecord.generation.asc())
    )
    return list(result.scalars().all())


async def get_reincarnation_status(session: AsyncSession, session_token: str) -> dict:
    """Inspect whether a session is ready for reincarnation and get available legacy."""
    token = session_token.strip() if session_token else ""
    if not token:
        raise ValidationError(
            "Session token cannot be empty or blank",
            details={"session_token": session_token},
        )
    session_res = await session.execute(
        select(GameSession).where(GameSession.session_token == token)
    )
    game_session = session_res.scalar_one_or_none()
    if game_session is None:
        raise NotFoundError("GameSession", session_token)
    if not game_session.is_active:
        raise ValidationError(
            "Game session has ended", details={"session_token": session_token}
        )

    # Check living character
    living_res = await session.execute(
        select(Character).where(
            Character.session_id == game_session.id,
            Character.is_alive.is_(True),
        )
    )
    living_char = living_res.scalar_one_or_none()

    # Find most recent character
    latest_char_res = await session.execute(
        select(Character)
        .where(Character.session_id == game_session.id)
        .order_by(Character.generation.desc())
    )
    latest_char = latest_char_res.scalars().first()

    available_legacy = None
    deceased_char_id = None
    if latest_char is not None and not latest_char.is_alive:
        deceased_char_id = latest_char.id
        legacy_res = await session.execute(
            select(CharacterLegacy).where(
                CharacterLegacy.character_id == latest_char.id
            )
        )
        available_legacy = legacy_res.scalar_one_or_none()

    can_reincarnate = (living_char is None) and (
        latest_char is not None and not latest_char.is_alive
    )

    return {
        "session_token": session_token,
        "current_generation": game_session.current_generation,
        "can_reincarnate": can_reincarnate,
        "living_character_id": living_char.id if living_char else None,
        "deceased_character_id": deceased_char_id,
        "available_legacy": available_legacy,
    }
