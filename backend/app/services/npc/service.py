"""Authoritative domain service for NPC interaction, dialogue, and relationships.

Implements NPC seeding, retrieval, dialogue generation, gifting, relationship
bounds (-100 to 100), trust tracking (0 to 100), and memory flags per SPEC.md §7.
"""

from typing import Any, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import GameStateError, NotFoundError, ValidationError
from app.models.enums import NPCPersonality, RaceName, TimeOfDay
from app.models.gameplay import (
    Character,
    GameplayState,
    InventoryItem,
    NPC,
    NPCRelationship,
)
from app.models.world import Location
from app.services.npc.definitions import NPC_DEFINITIONS


def get_relationship_tier(value: int, trust: int) -> str:
    """Classify relationship numerical values into human-readable narrative tiers."""
    if value < -40:
        return "Hostile"
    elif value < -10:
        return "Unfriendly"
    elif value < 30:
        return "Neutral"
    elif value < 70:
        return "Friendly"
    elif trust >= 60 and value >= 70:
        return "Devoted"
    else:
        return "Trusted"


async def ensure_npcs_seeded(session: AsyncSession) -> list[NPC]:
    """Ensure all predefined NPCs are seeded into the database and linked to locations.

    Idempotent: flushes created entities without committing (caller owns transaction).
    """
    count = await session.scalar(select(func.count(NPC.id)))
    if count is not None and count >= len(NPC_DEFINITIONS):
        result = await session.execute(
            select(NPC).options(selectinload(NPC.location)).order_by(NPC.id)
        )
        return list(result.scalars().all())

    # Map existing locations by name
    loc_res = await session.execute(select(Location))
    locations = {loc.name: loc for loc in loc_res.scalars().all()}

    # Query existing NPC names to avoid duplicates
    existing_res = await session.execute(select(NPC.name))
    existing_names = set(existing_res.scalars().all())

    for npc_data in NPC_DEFINITIONS:
        if npc_data["name"] in existing_names:
            continue

        loc_name = npc_data["location_name"]
        location = locations.get(loc_name)
        if location is None:
            continue

        # Convert available times to list of strings
        available_times = [
            t.value if isinstance(t, TimeOfDay) else str(t)
            for t in npc_data.get("available_times", [])
        ]

        npc = NPC(
            name=npc_data["name"],
            race_name=(
                npc_data["race_name"]
                if isinstance(npc_data["race_name"], RaceName)
                else RaceName(npc_data["race_name"])
            ),
            age=npc_data["age"],
            personality=(
                npc_data["personality"]
                if isinstance(npc_data["personality"], NPCPersonality)
                else NPCPersonality(npc_data["personality"])
            ),
            occupation=npc_data["occupation"],
            location_id=location.id,
            description=npc_data["description"],
            background_story=npc_data["background_story"],
            greeting=npc_data["greeting"],
            dialogue_lines=npc_data["dialogue_lines"],
            farewell=npc_data["farewell"],
            min_relationship=npc_data.get("min_relationship", -100),
            max_relationship=npc_data.get("max_relationship", 100),
            available_times=available_times,
            is_essential=npc_data.get("is_essential", False),
            strength=npc_data.get("strength", 10),
            agility=npc_data.get("agility", 10),
            intelligence=npc_data.get("intelligence", 10),
            vitality=npc_data.get("vitality", 10),
        )
        session.add(npc)

    await session.flush()

    res = await session.execute(
        select(NPC).options(selectinload(NPC.location)).order_by(NPC.id)
    )
    return list(res.scalars().all())


async def get_npcs_by_location(
    session: AsyncSession,
    location_id: int,
    character_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Retrieve all NPCs present at a location with optional relationship data."""
    await ensure_npcs_seeded(session)

    res = await session.execute(
        select(NPC)
        .options(selectinload(NPC.location))
        .where(NPC.location_id == location_id)
        .order_by(NPC.id)
    )
    npcs = list(res.scalars().all())

    # If character_id provided, load relationships
    rel_map: dict[int, NPCRelationship] = {}
    if character_id is not None:
        rel_res = await session.execute(
            select(NPCRelationship).where(
                NPCRelationship.character_id == character_id,
                NPCRelationship.npc_id.in_([npc.id for npc in npcs]),
            )
        )
        rel_map = {rel.npc_id: rel for rel in rel_res.scalars().all()}

    output = []
    for npc in npcs:
        rel = rel_map.get(npc.id)
        output.append(
            {
                "id": npc.id,
                "name": npc.name,
                "race_name": (
                    npc.race_name.value
                    if hasattr(npc.race_name, "value")
                    else str(npc.race_name)
                ),
                "age": npc.age,
                "personality": (
                    npc.personality.value
                    if hasattr(npc.personality, "value")
                    else str(npc.personality)
                ),
                "occupation": npc.occupation,
                "location_id": npc.location_id,
                "location_name": npc.location.name if npc.location else "Unknown",
                "is_essential": npc.is_essential,
                "relationship_value": rel.value if rel else 0,
                "trust": rel.trust if rel else 0,
                "available_times": npc.available_times or [],
            }
        )

    return output


async def get_or_create_relationship(
    session: AsyncSession,
    character_id: int,
    npc_id: int,
) -> NPCRelationship:
    """Retrieve or initialize an NPCRelationship for a given character and NPC."""
    res = await session.execute(
        select(NPCRelationship).where(
            NPCRelationship.character_id == character_id,
            NPCRelationship.npc_id == npc_id,
        )
    )
    rel = res.scalar_one_or_none()
    if rel is None:
        rel = NPCRelationship(
            character_id=character_id,
            npc_id=npc_id,
            value=0,
            trust=0,
            memory_flags={},
        )
        session.add(rel)
        await session.flush()
        await session.refresh(rel)
    return rel


async def get_npc_profile(
    session: AsyncSession,
    npc_id: int,
    character_id: Optional[int] = None,
) -> dict[str, Any]:
    """Retrieve complete profile of an NPC and the player's relationship with them."""
    await ensure_npcs_seeded(session)

    res = await session.execute(
        select(NPC).options(selectinload(NPC.location)).where(NPC.id == npc_id)
    )
    npc = res.scalar_one_or_none()
    if npc is None:
        raise NotFoundError("NPC", npc_id)

    rel_value = 0
    trust_val = 0
    memory_flags: dict[str, bool] = {}

    if character_id is not None:
        rel = await get_or_create_relationship(session, character_id, npc_id)
        rel_value = rel.value
        trust_val = rel.trust
        memory_flags = dict(rel.memory_flags or {})

    return {
        "id": npc.id,
        "name": npc.name,
        "race_name": (
            npc.race_name.value
            if hasattr(npc.race_name, "value")
            else str(npc.race_name)
        ),
        "age": npc.age,
        "personality": (
            npc.personality.value
            if hasattr(npc.personality, "value")
            else str(npc.personality)
        ),
        "occupation": npc.occupation,
        "location_id": npc.location_id,
        "location_name": npc.location.name if npc.location else "Unknown",
        "description": npc.description,
        "background_story": npc.background_story,
        "greeting": npc.greeting,
        "farewell": npc.farewell,
        "available_times": npc.available_times or [],
        "is_essential": npc.is_essential,
        "relationship_value": rel_value,
        "trust": trust_val,
        "memory_flags": memory_flags,
    }


async def talk_to_npc(
    session: AsyncSession,
    character_id: int,
    npc_id: int,
    topic: Optional[str] = None,
) -> dict[str, Any]:
    """Engage in dialogue with an NPC.

    Authoritative: updates relationship, trust, sets memory flags, and flushes to database.
    """
    await ensure_npcs_seeded(session)

    # 1. Load NPC
    npc_res = await session.execute(
        select(NPC).options(selectinload(NPC.location)).where(NPC.id == npc_id)
    )
    npc = npc_res.scalar_one_or_none()
    if npc is None:
        raise NotFoundError("NPC", npc_id)

    # 2. Load Character
    char = await session.get(Character, character_id)
    if char is None:
        raise NotFoundError("Character", character_id)
    if not char.is_alive:
        raise GameStateError("Deceased characters cannot interact with NPCs.")

    # 3. Load GameplayState for time
    state_res = await session.execute(
        select(GameplayState).where(GameplayState.character_id == character_id)
    )
    gameplay_state = state_res.scalar_one_or_none()
    current_period = (
        gameplay_state.current_time_of_day.value if gameplay_state else None
    )

    # 4. Load or create relationship
    rel = await get_or_create_relationship(session, character_id, npc_id)
    flags = dict(rel.memory_flags or {})

    # 5. Determine dynamic greeting
    is_first_meeting = not flags.get("met_character", False)
    if is_first_meeting:
        flags["met_character"] = True
        greeting = npc.greeting
    elif rel.value >= 30:
        greeting = f"Welcome back, friend! It is always a pleasure to speak with you. {npc.greeting}"
    elif rel.value <= -20:
        greeting = f"You again? Make your business brief. {npc.greeting}"
    else:
        greeting = npc.greeting

    # 6. Select dialogue line
    lines = npc.dialogue_lines or ["I have nothing more to say right now."]
    if is_first_meeting:
        dialogue = lines[0]
    else:
        flags["spoken_again"] = True
        dialogue = lines[1 % len(lines)]

    if topic:
        flags[f"discussed_{topic.lower()}"] = True
        dialogue = f"[Topic: {topic}] {dialogue}"

    # 7. Calculate relationship and trust changes based on personality
    pers = npc.personality
    if pers == NPCPersonality.FRIENDLY:
        rel_delta = 4
        trust_delta = 3
    elif pers == NPCPersonality.COMPASSIONATE:
        rel_delta = 3
        trust_delta = 3
    elif pers == NPCPersonality.SUSPICIOUS:
        rel_delta = 2
        trust_delta = 1
    elif pers == NPCPersonality.ARROGANT:
        rel_delta = 2
        trust_delta = 1
    elif pers == NPCPersonality.GREEDY:
        rel_delta = 1
        trust_delta = 1
    elif pers == NPCPersonality.MANIPULATIVE:
        rel_delta = 2
        trust_delta = 2
    else:
        rel_delta = 2
        trust_delta = 1

    # Apply deltas within bounds
    old_value = rel.value
    old_trust = rel.trust

    rel.value = max(
        npc.min_relationship, min(npc.max_relationship, rel.value + rel_delta)
    )
    rel.trust = max(0, min(100, rel.trust + trust_delta))
    rel.memory_flags = flags

    await session.flush()

    return {
        "npc_id": npc.id,
        "npc_name": npc.name,
        "greeting": greeting,
        "dialogue": dialogue,
        "farewell": npc.farewell,
        "relationship_value": rel.value,
        "trust": rel.trust,
        "relationship_change": rel.value - old_value,
        "trust_change": rel.trust - old_trust,
        "memory_flags": flags,
        "current_period": current_period,
    }


async def give_gift_to_npc(
    session: AsyncSession,
    character_id: int,
    npc_id: int,
    item_name: Optional[str] = None,
    money: int = 0,
) -> dict[str, Any]:
    """Give a monetary or item gift to an NPC.

    Authoritative: validates inventory/funds, updates character state, updates
    NPC relationship and trust, sets memory flags, and flushes to database.
    """
    await ensure_npcs_seeded(session)

    # 1. Load NPC
    npc_res = await session.execute(
        select(NPC).options(selectinload(NPC.location)).where(NPC.id == npc_id)
    )
    npc = npc_res.scalar_one_or_none()
    if npc is None:
        raise NotFoundError("NPC", npc_id)

    # 2. Load Character
    char = await session.get(Character, character_id)
    if char is None:
        raise NotFoundError("Character", character_id)
    if not char.is_alive:
        raise GameStateError("Deceased characters cannot gift NPCs.")

    if money <= 0 and not item_name:
        raise ValidationError("Must provide a gift of money or an item name.")

    # 3. Load or create relationship
    rel = await get_or_create_relationship(session, character_id, npc_id)
    flags = dict(rel.memory_flags or {})

    old_value = rel.value
    old_trust = rel.trust
    gift_accepted = True
    message = ""
    item_gifted_name = None

    # Handle money gift
    if money > 0:
        if char.money < money:
            raise ValidationError(
                f"Insufficient funds: character has {char.money} gold, needs {money} gold."
            )
        char.money -= money

        pers = npc.personality
        if pers == NPCPersonality.GREEDY:
            rel_delta = min(30, max(5, money // 2))
            trust_delta = min(20, max(3, money // 4))
            message = (
                f"Marcus chuckles greedily, pocketing the {money} gold with delight."
            )
        elif pers == NPCPersonality.COMPASSIONATE:
            rel_delta = min(20, max(4, money // 4))
            trust_delta = min(15, max(3, money // 5))
            message = f"Touched by your generosity, {npc.name} graciously accepts the {money} gold to support local folk."
        elif pers == NPCPersonality.ARROGANT:
            if money < 20:
                rel_delta = 1
                trust_delta = 0
                message = f"{npc.name} glances at the {money} gold disdainfully: 'A meager offering, but noted.'"
            else:
                rel_delta = min(20, money // 4)
                trust_delta = min(12, money // 6)
                message = f"{npc.name} nods with stately approval at your substantial offering of {money} gold."
        elif pers == NPCPersonality.SUSPICIOUS:
            if money > 50 and rel.trust < 20:
                rel_delta = 0
                trust_delta = -2
                message = f"{npc.name} eyes the {money} gold warily: 'What strings are attached to this coin?'"
            else:
                rel_delta = min(15, money // 4)
                trust_delta = min(10, money // 6)
                message = (
                    f"{npc.name} accepts the {money} gold after thorough inspection."
                )
        else:
            rel_delta = min(20, max(3, money // 4))
            trust_delta = min(15, max(2, money // 5))
            message = f"{npc.name} warmly thanks you for the {money} gold gift."

        flags["received_gift"] = True
        if money >= 50:
            flags["generous_patron"] = True

    # Handle item gift
    elif item_name:
        item_res = await session.execute(
            select(InventoryItem).where(
                InventoryItem.character_id == character_id,
                InventoryItem.name == item_name,
            )
        )
        inv_item = item_res.scalar_one_or_none()
        if inv_item is None or inv_item.quantity < 1:
            raise ValidationError(f"Item '{item_name}' is not in character inventory.")

        # Remove 1 from inventory
        if inv_item.quantity > 1:
            inv_item.quantity -= 1
        else:
            await session.delete(inv_item)

        item_gifted_name = item_name
        rel_delta = 10
        trust_delta = 8
        message = (
            f"{npc.name} is deeply appreciative of your thoughtful gift: {item_name}."
        )
        flags["received_gift"] = True
        flags[f"gifted_{item_name.lower().replace(' ', '_')}"] = True

    # Apply relationship & trust changes
    rel.value = max(
        npc.min_relationship, min(npc.max_relationship, rel.value + rel_delta)
    )
    rel.trust = max(0, min(100, rel.trust + trust_delta))
    rel.memory_flags = flags

    await session.flush()

    return {
        "npc_id": npc.id,
        "npc_name": npc.name,
        "message": message,
        "gift_accepted": gift_accepted,
        "money_gifted": money,
        "item_gifted": item_gifted_name,
        "relationship_value": rel.value,
        "trust": rel.trust,
        "relationship_change": rel.value - old_value,
        "trust_change": rel.trust - old_trust,
        "remaining_money": char.money,
        "memory_flags": flags,
    }


async def get_all_character_relationships(
    session: AsyncSession,
    character_id: int,
) -> list[dict[str, Any]]:
    """Retrieve all recorded relationships for a character."""
    await ensure_npcs_seeded(session)

    res = await session.execute(
        select(NPCRelationship)
        .options(selectinload(NPCRelationship.npc).selectinload(NPC.location))
        .where(NPCRelationship.character_id == character_id)
        .order_by(NPCRelationship.value.desc())
    )
    relationships = list(res.scalars().all())

    summaries = []
    for rel in relationships:
        npc = rel.npc
        loc_name = npc.location.name if npc.location else "Unknown"
        tier = get_relationship_tier(rel.value, rel.trust)
        summaries.append(
            {
                "npc_id": npc.id,
                "npc_name": npc.name,
                "occupation": npc.occupation,
                "location_name": loc_name,
                "relationship_value": rel.value,
                "trust": rel.trust,
                "relationship_tier": tier,
                "memory_flags": dict(rel.memory_flags or {}),
            }
        )

    return summaries
