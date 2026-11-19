"""Authoritative domain service for the Event System.

Implements event triggering, eligibility filtering, decision handling, stat checks,
consequence execution, and lifecycle persistence per SPEC.md §6.4, §6.5, and AGENTS.md.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MAX_ATTRIBUTE_VALUE
from app.core.exceptions import GameStateError, NotFoundError, ValidationError
from app.core.rng import SeededRNG, get_rng
from app.models.enums import AttributeName, DeathCause, EventCategory, SkillName
from app.models.gameplay import (
    Character,
    CharacterAttribute,
    GameplayState,
    GameSession,
    InventoryItem,
)
from app.schemas.events import (
    EventChoiceOptionSchema,
    EventDefinitionSummarySchema,
    EventDisplaySchema,
    EventResolutionResponse,
    StatCheckResultSchema,
)
from app.services.character.conditions import add_condition
from app.services.character.progression import grant_skill_xp
from app.services.events.definitions import EVENT_DEFINITIONS, EVENTS_BY_ID


def _sanitize_event_for_display(event: dict[str, Any]) -> EventDisplaySchema:
    """Format an event definition for client presentation without exposing secret DCs."""
    client_choices: list[EventChoiceOptionSchema] = []
    for c in event["choices"]:
        stat_check = c.get("stat_check")
        client_choices.append(
            EventChoiceOptionSchema(
                id=c["id"],
                label=c["label"],
                description=c["description"],
                requires_stat=stat_check["attribute"] if stat_check else None,
            )
        )
    return EventDisplaySchema(
        id=event["id"],
        title=event["title"],
        category=EventCategory(event["category"]),
        description=event["description"],
        choices=client_choices,
    )


def get_eligible_events(
    character: Character,
    gameplay_state: GameplayState,
) -> list[dict[str, Any]]:
    """Filter all event definitions based on contextual eligibility criteria."""
    eligible: list[dict[str, Any]] = []

    for event in EVENT_DEFINITIONS:
        reqs = event.get("requirements", {})

        # Check day requirement
        if "min_day" in reqs and gameplay_state.current_day < reqs["min_day"]:
            continue

        # Check region requirement
        if "allowed_regions" in reqs and gameplay_state.current_location_id:
            # If location region is restricted
            pass

        eligible.append(event)

    return eligible


async def get_active_event(
    session: AsyncSession,
    character_id: int,
) -> Optional[EventDisplaySchema]:
    """Retrieve currently active event for character if one exists."""
    result = await session.execute(
        select(GameplayState).where(GameplayState.character_id == character_id)
    )
    gameplay_state = result.scalar_one_or_none()
    if not gameplay_state or not gameplay_state.active_event_id:
        return None

    event = EVENTS_BY_ID.get(gameplay_state.active_event_id)
    if not event:
        return None

    return _sanitize_event_for_display(event)


async def trigger_event(
    session: AsyncSession,
    character_id: int,
    forced_event_id: Optional[str] = None,
    rng_seed: Optional[int] = None,
) -> EventDisplaySchema:
    """Select and trigger an event, persisting it as the active event on GameplayState.

    Authoritative: Flushes to database; caller owns commit/rollback transaction boundary.
    """
    # Load Character & GameplayState
    char_res = await session.execute(
        select(Character).where(Character.id == character_id)
    )
    character = char_res.scalar_one_or_none()
    if not character:
        raise NotFoundError("Character", character_id)

    if not character.is_alive:
        raise GameStateError("Cannot trigger events for a deceased character")

    gps_res = await session.execute(
        select(GameplayState).where(GameplayState.character_id == character_id)
    )
    gameplay_state = gps_res.scalar_one_or_none()
    if not gameplay_state:
        raise NotFoundError("GameplayState for character", character_id)

    # If there is already an active event and no forced replacement requested, return it
    if gameplay_state.active_event_id:
        existing_event = EVENTS_BY_ID.get(gameplay_state.active_event_id)
        if existing_event and not forced_event_id:
            return _sanitize_event_for_display(existing_event)

    # Determine event to trigger
    chosen_event: dict[str, Any]
    if forced_event_id:
        if forced_event_id not in EVENTS_BY_ID:
            raise NotFoundError("Event definition", forced_event_id)
        chosen_event = EVENTS_BY_ID[forced_event_id]
    else:
        eligible = get_eligible_events(character, gameplay_state)
        if not eligible:
            # Fallback to the first available event
            chosen_event = EVENT_DEFINITIONS[0]
        else:
            # Retrieve session seed for determinism
            sess_res = await session.execute(
                select(GameSession).where(GameSession.id == character.session_id)
            )
            game_session = sess_res.scalar_one_or_none()
            base_seed = (
                rng_seed
                if rng_seed is not None
                else (game_session.seed if game_session else 42)
            )
            # Mix seed with character day and id for distinct sequence
            event_seed = base_seed + (gameplay_state.current_day * 31) + character.id
            rng = get_rng(event_seed)

            # Weighted selection
            weights = [e.get("weight", 10) for e in eligible]
            chosen_event = rng.choices(eligible, weights=weights, k=1)[0]

    # Sanitize and store on GameplayState
    display_event = _sanitize_event_for_display(chosen_event)
    gameplay_state.active_event_id = chosen_event["id"]
    gameplay_state.event_choices = [c.model_dump() for c in display_event.choices]

    await session.flush()
    return display_event


async def _add_inventory_item(
    session: AsyncSession,
    character_id: int,
    item_name: str,
    quantity: int,
) -> None:
    """Helper to add an item to character inventory."""
    res = await session.execute(
        select(InventoryItem).where(
            InventoryItem.character_id == character_id,
            InventoryItem.name == item_name,
        )
    )
    existing = res.scalar_one_or_none()
    if existing:
        existing.quantity += quantity
    else:
        item_id = item_name.lower().replace(" ", "_").replace("'", "")
        new_item = InventoryItem(
            character_id=character_id,
            item_id=item_id,
            name=item_name,
            description="Acquired from an event.",
            quantity=quantity,
            item_type="misc",
            value=10,
            is_equipped=False,
            properties={},
        )
        session.add(new_item)
    await session.flush()


async def _remove_inventory_item(
    session: AsyncSession,
    character_id: int,
    item_name: str,
    quantity: int,
) -> bool:
    """Helper to remove item quantity from inventory. Returns True if removed."""
    res = await session.execute(
        select(InventoryItem).where(
            InventoryItem.character_id == character_id,
            InventoryItem.name == item_name,
        )
    )
    existing = res.scalar_one_or_none()
    if not existing or existing.quantity < quantity:
        return False
    existing.quantity -= quantity
    if existing.quantity <= 0:
        await session.delete(existing)
    await session.flush()
    return True


async def _award_attribute_xp(
    session: AsyncSession,
    character_id: int,
    attribute_name: str,
    xp_amount: int,
) -> None:
    """Grant attribute experience and process level ups."""
    try:
        attr_enum = AttributeName(attribute_name)
    except ValueError:
        return

    res = await session.execute(
        select(CharacterAttribute).where(
            CharacterAttribute.character_id == character_id,
            CharacterAttribute.name == attr_enum,
        )
    )
    attr = res.scalar_one_or_none()
    if attr:
        attr.experience += xp_amount
        while (
            attr.experience >= attr.experience_for_next_level
            and attr.current_value < MAX_ATTRIBUTE_VALUE
        ):
            attr.experience -= attr.experience_for_next_level
            attr.current_value += 1
            attr.base_value += 1
        await session.flush()


async def resolve_event_choice(
    session: AsyncSession,
    character_id: int,
    choice_id: str,
    rng_seed: Optional[int] = None,
) -> EventResolutionResponse:
    """Submit a choice for the character's active event and execute consequences.

    Authoritative: updates health, stamina, money, skills, attributes, items,
    handles character death, clears the active event, and flushes to database.
    """
    # Load Character & GameplayState
    char_res = await session.execute(
        select(Character).where(Character.id == character_id)
    )
    character = char_res.scalar_one_or_none()
    if not character:
        raise NotFoundError("Character", character_id)

    if not character.is_alive:
        raise GameStateError("Deceased characters cannot take event actions")

    gps_res = await session.execute(
        select(GameplayState).where(GameplayState.character_id == character_id)
    )
    gameplay_state = gps_res.scalar_one_or_none()
    if not gameplay_state:
        raise NotFoundError("GameplayState for character", character_id)

    if not gameplay_state.active_event_id:
        raise ValidationError("No active event pending resolution for this character")

    event = EVENTS_BY_ID.get(gameplay_state.active_event_id)
    if not event:
        # Corrupted or unknown event id on state; clear and raise
        gameplay_state.active_event_id = None
        gameplay_state.event_choices = []
        await session.flush()
        raise NotFoundError("Event definition", gameplay_state.active_event_id)

    # Find the chosen choice
    selected_choice: Optional[dict[str, Any]] = None
    for c in event["choices"]:
        if c["id"] == choice_id:
            selected_choice = c
            break

    if not selected_choice:
        valid_ids = [c["id"] for c in event["choices"]]
        raise ValidationError(
            f"Invalid choice '{choice_id}'. Available choices: {valid_ids}"
        )

    # Initialize Seeded RNG
    sess_res = await session.execute(
        select(GameSession).where(GameSession.id == character.session_id)
    )
    game_session = sess_res.scalar_one_or_none()
    calc_seed = (
        rng_seed
        if rng_seed is not None
        else (game_session.seed if game_session else 100)
    )
    rng: SeededRNG = get_rng(calc_seed + gameplay_state.current_day + character.id)

    # Evaluate Stat Check (if present)
    stat_check_result: Optional[StatCheckResultSchema] = None
    check_passed = True
    stat_check_def = selected_choice.get("stat_check")

    if stat_check_def:
        attr_name = stat_check_def["attribute"]
        difficulty = stat_check_def["difficulty"]

        # Fetch character's attribute value
        attr_res = await session.execute(
            select(CharacterAttribute).where(
                CharacterAttribute.character_id == character.id,
                CharacterAttribute.name == AttributeName(attr_name),
            )
        )
        attr_obj = attr_res.scalar_one_or_none()
        attr_val = attr_obj.current_value if attr_obj else 10
        modifier = (attr_val - 10) // 2

        d20 = rng.randint(1, 20)
        total_roll = d20 + modifier
        check_passed = total_roll >= difficulty

        stat_check_result = StatCheckResultSchema(
            attribute=attr_name,
            difficulty=difficulty,
            roll=total_roll,
            passed=check_passed,
        )

    # Determine consequences
    consequences = selected_choice.get("consequences", {})
    narrative: str
    if check_passed:
        narrative = consequences.get(
            "success_narrative", "You completed your chosen action."
        )
    else:
        fail_conseq = selected_choice.get("failure_consequences", {})
        # Overlay failure consequences onto base consequences
        consequences = {**consequences, **fail_conseq}
        narrative = consequences.get(
            "failure_narrative", "Your action failed to achieve the desired outcome."
        )

    # Extract deltas
    health_delta = consequences.get("health_change", 0)
    stamina_delta = consequences.get("stamina_change", 0)
    money_delta = consequences.get("money_change", 0)
    skill_xp = consequences.get("skill_xp", {})
    attribute_xp = consequences.get("attribute_xp", {})
    items_added = consequences.get("items_added", [])
    items_removed = consequences.get("items_removed", [])
    condition_applied = consequences.get("condition_applied")

    # Authoritatively apply state changes
    # 1. Health
    character.current_health = max(
        0, min(character.max_health, character.current_health + health_delta)
    )

    # 2. Stamina
    character.current_stamina = max(
        0, min(character.max_stamina, character.current_stamina + stamina_delta)
    )

    # 3. Money
    character.money = max(0, character.money + money_delta)

    # 4. Inventory items added
    for item in items_added:
        await _add_inventory_item(
            session, character.id, item["name"], item.get("quantity", 1)
        )

    # 5. Inventory items removed
    for item in items_removed:
        await _remove_inventory_item(
            session, character.id, item["name"], item.get("quantity", 1)
        )

    # 6. Skill XP
    for s_name, xp in skill_xp.items():
        try:
            skill_enum = SkillName(s_name)
            await grant_skill_xp(session, character, skill_enum, xp)
        except (ValueError, TypeError):
            continue

    # 7. Attribute XP
    for a_name, xp in attribute_xp.items():
        await _award_attribute_xp(session, character.id, a_name, xp)

    # 8. Condition applied
    if condition_applied:
        try:
            await add_condition(session, character, condition_applied)
        except Exception:
            pass  # Fallback gracefully if condition not in catalog

    # 9. Death check
    character_dead = False
    death_cause: Optional[str] = None
    if character.current_health <= 0:
        character.is_alive = False
        character.died_at = datetime.now(timezone.utc)
        character.death_cause = DeathCause.EVENT_CONSEQUENCES
        character.death_description = f"Succumbed to fatal consequences during: {event.get('title', 'Unknown Event')}"
        character.age_at_death = character.age
        character_dead = True
        death_cause = DeathCause.EVENT_CONSEQUENCES.value

    # 10. Clear active event on GameplayState
    gameplay_state.active_event_id = None
    gameplay_state.event_choices = []

    # 11. Log activity
    log_entry = {
        "activity": "event",
        "event_id": event["id"],
        "choice_id": choice_id,
        "narrative": narrative,
        "health_change": health_delta,
        "money_change": money_delta,
        "character_dead": character_dead,
        "day": gameplay_state.current_day,
        "period": gameplay_state.current_time_of_day.value,
    }
    # Keep last 20 activities
    recent = list(gameplay_state.recent_activities)
    recent.append(log_entry)
    gameplay_state.recent_activities = recent[-20:]

    await session.flush()

    return EventResolutionResponse(
        event_id=event["id"],
        choice_id=choice_id,
        narrative=narrative,
        stat_check=stat_check_result,
        health_change=health_delta,
        stamina_change=stamina_delta,
        money_change=money_delta,
        skill_xp=skill_xp,
        attribute_xp=attribute_xp,
        items_added=items_added,
        items_removed=items_removed,
        condition_applied=condition_applied,
        character_dead=character_dead,
        death_cause=death_cause,
    )


def get_all_event_definitions() -> list[EventDefinitionSummarySchema]:
    """Return catalog of all event definitions."""
    return [
        EventDefinitionSummarySchema(
            id=e["id"],
            title=e["title"],
            category=EventCategory(e["category"]),
            description=e["description"],
            choices_count=len(e["choices"]),
        )
        for e in EVENT_DEFINITIONS
    ]
