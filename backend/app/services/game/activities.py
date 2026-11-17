"""Basic activities service: Explore, Rest, Work."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError, NotFoundError
from app.core.rng import get_rng
from app.models.enums import (
    TimeOfDay,
    SkillName,
    AttributeName,
    ActivityType,
)
from app.models.gameplay import (
    Character,
    CharacterSkill,
    InventoryItem,
    GameplayState,
)
from app.models.world import Location
from app.services.game.time import advance_time
from app.services.character.progression import grant_character_xp, grant_skill_xp
from app.services.character.resources import (
    consume_stamina,
    restore_stamina,
    increase_fatigue,
    reduce_fatigue,
    get_effective_stamina,
)
from app.services.character.conditions import apply_condition_effects
from app.services.character.inventory import (
    add_money,
    add_item,
)


# Activity time costs (in periods)
ACTIVITY_TIME_COSTS = {
    ActivityType.EXPLORE: 1,
    ActivityType.REST: 2,  # Long rest
    ActivityType.REST_SHORT: 1,  # Short rest
    ActivityType.WORK: 1,
    ActivityType.TRAIN: 1,
    ActivityType.TRADE: 1,
    ActivityType.SOCIALIZE: 1,
    ActivityType.HUNT_MONSTERS: 2,
    ActivityType.ACCEPT_QUEST: 1,
    ActivityType.VISIT_LOCATION: 0,  # Handled by travel
}

# Stamina costs for activities (base cost, modified by fatigue)
ACTIVITY_STAMINA_COSTS = {
    ActivityType.EXPLORE: 15,
    ActivityType.REST: 0,  # Rest restores stamina
    ActivityType.REST_SHORT: 0,
    ActivityType.WORK: 20,
    ActivityType.TRAIN: 25,
    ActivityType.TRADE: 10,
    ActivityType.SOCIALIZE: 5,
    ActivityType.HUNT_MONSTERS: 30,
    ActivityType.ACCEPT_QUEST: 5,
    ActivityType.VISIT_LOCATION: 0,
}

# Fatigue increase per activity
ACTIVITY_FATIGUE_INCREASE = {
    ActivityType.EXPLORE: 1,
    ActivityType.REST: -2,  # Rest reduces fatigue
    ActivityType.REST_SHORT: -1,
    ActivityType.WORK: 1,
    ActivityType.TRAIN: 2,
    ActivityType.TRADE: 0,
    ActivityType.SOCIALIZE: 0,
    ActivityType.HUNT_MONSTERS: 2,
    ActivityType.ACCEPT_QUEST: 0,
    ActivityType.VISIT_LOCATION: 0,
}


async def _validate_stamina_for_activity(
    character: Character, activity_type: ActivityType
) -> None:
    """Validate that character has sufficient effective stamina for an activity.

    Args:
        character: Character attempting the activity
        activity_type: Type of activity

    Raises:
        ValidationError: If effective stamina is insufficient
    """
    required_stamina = ACTIVITY_STAMINA_COSTS.get(activity_type, 0)
    if required_stamina <= 0:
        return  # No stamina requirement (e.g., rest)

    effective_max = await get_effective_stamina(character)
    available_stamina = min(character.current_stamina, effective_max)
    if available_stamina < required_stamina:
        raise ValidationError(
            f"Insufficient stamina for {activity_type.value}",
            details={
                "required_stamina": required_stamina,
                "current_stamina": character.current_stamina,
                "effective_stamina": available_stamina,
                "effective_max_stamina": effective_max,
            },
        )


# Work types and their base rewards by location type
WORK_TYPES = {
    "city": [
        {
            "name": "Laborer",
            "base_money": 15,
            "skill": "survival",
            "attr": "strength",
            "description": "Heavy lifting and construction work",
        },
        {
            "name": "Clerk",
            "base_money": 20,
            "skill": "trading",
            "attr": "intelligence",
            "description": "Record keeping and administration",
        },
        {
            "name": "Guard",
            "base_money": 25,
            "skill": "swordsmanship",
            "attr": "strength",
            "description": "Patrolling and keeping order",
        },
    ],
    "market": [
        {
            "name": "Shop Assistant",
            "base_money": 18,
            "skill": "trading",
            "attr": "intelligence",
            "description": "Helping customers and managing inventory",
        },
        {
            "name": "Porter",
            "base_money": 15,
            "skill": "survival",
            "attr": "strength",
            "description": "Moving goods between stalls",
        },
        {
            "name": "Appraiser Assistant",
            "base_money": 22,
            "skill": "trading",
            "attr": "intelligence",
            "description": "Evaluating trade goods",
        },
    ],
    "academy": [
        {
            "name": "Library Assistant",
            "base_money": 15,
            "skill": "magic",
            "attr": "intelligence",
            "description": "Organizing magical tomes and scrolls",
        },
        {
            "name": "Lab Assistant",
            "base_money": 20,
            "skill": "healing",
            "attr": "intelligence",
            "description": "Preparing alchemical reagents",
        },
        {
            "name": "Messenger",
            "base_money": 12,
            "skill": "survival",
            "attr": "agility",
            "description": "Delivering messages between towers",
        },
    ],
    "outpost": [
        {
            "name": "Miner",
            "base_money": 30,
            "skill": "crafting",
            "attr": "strength",
            "description": "Extracting ore from the Silvervein Mines",
        },
        {
            "name": "Caravan Guard",
            "base_money": 25,
            "skill": "swordsmanship",
            "attr": "strength",
            "description": "Protecting supply caravans",
        },
        {
            "name": "Smith Assistant",
            "base_money": 20,
            "skill": "crafting",
            "attr": "strength",
            "description": "Helping forge weapons and armor",
        },
    ],
    "ruins": [
        {
            "name": "Scavenger",
            "base_money": 20,
            "skill": "survival",
            "attr": "agility",
            "description": "Searching ruins for valuable remnants",
        },
        {
            "name": "Ruins Guard",
            "base_money": 35,
            "skill": "swordsmanship",
            "attr": "strength",
            "description": "Protecting expedition teams",
        },
    ],
    "village": [
        {
            "name": "Farmhand",
            "base_money": 12,
            "skill": "survival",
            "attr": "strength",
            "description": "Helping with crops and livestock",
        },
        {
            "name": "Crafts Assistant",
            "base_money": 15,
            "skill": "crafting",
            "attr": "intelligence",
            "description": "Assisting local artisans",
        },
        {
            "name": "Herbalist Helper",
            "base_money": 18,
            "skill": "healing",
            "attr": "intelligence",
            "description": "Gathering and preparing herbs",
        },
    ],
    "shrine": [
        {
            "name": "Shrine Keeper",
            "base_money": 10,
            "skill": "healing",
            "attr": "intelligence",
            "description": "Maintaining the shrine grounds",
        },
        {
            "name": "Pilgrim Guide",
            "base_money": 15,
            "skill": "survival",
            "attr": "agility",
            "description": "Guiding visitors through sacred paths",
        },
    ],
}


# Exploration discoveries by location type
EXPLORATION_DISCOVERIES = {
    "city": [
        {
            "name": "Hidden Alleyway",
            "description": "A narrow passage behind the market",
            "money": 5,
            "xp": {"survival": 5},
        },
        {
            "name": "Abandoned Cellar",
            "description": "Old storage with forgotten goods",
            "money": 10,
            "items": [{"name": "Old Wine", "quantity": 1, "value": 8}],
        },
        {
            "name": "Guild Bulletin",
            "description": "New contracts posted",
            "money": 0,
            "xp": {"negotiation": 10},
        },
    ],
    "market": [
        {
            "name": "Dropped Coin Purse",
            "description": "Someone's lost money",
            "money": 15,
            "xp": {"trading": 5},
        },
        {
            "name": "Rare Spice Sample",
            "description": "A merchant's free sample",
            "money": 0,
            "items": [{"name": "Exotic Spice", "quantity": 1, "value": 20}],
        },
        {
            "name": "Market Gossip",
            "description": "Useful trade information",
            "money": 0,
            "xp": {"negotiation": 10, "trading": 5},
        },
    ],
    "academy": [
        {
            "name": "Lost Spell Fragment",
            "description": "A torn page from a spellbook",
            "money": 0,
            "items": [{"name": "Spell Fragment", "quantity": 1, "value": 50}],
            "xp": {"magic": 15},
        },
        {
            "name": "Alchemical Residue",
            "description": "Glowing residue from an experiment",
            "money": 0,
            "items": [{"name": "Alchemical Residue", "quantity": 1, "value": 30}],
        },
        {
            "name": "Lecture Notes",
            "description": "Abandoned student notes",
            "money": 0,
            "xp": {"magic": 10, "healing": 5},
        },
    ],
    "outpost": [
        {
            "name": "Ore Sample",
            "description": "A chunk of rich ore",
            "money": 0,
            "items": [{"name": "Iron Ore", "quantity": 2, "value": 10}],
        },
        {
            "name": "Abandoned Gear",
            "description": "Equipment left by a miner",
            "money": 0,
            "items": [{"name": "Miner's Pick", "quantity": 1, "value": 15}],
        },
        {
            "name": "Strange Tracks",
            "description": "Large beast tracks near the mine",
            "money": 0,
            "xp": {"survival": 15},
        },
    ],
    "ruins": [
        {
            "name": "Ancient Coin",
            "description": "A coin from the dwarven kingdom",
            "money": 25,
            "items": [{"name": "Dwarven Coin", "quantity": 1, "value": 30}],
        },
        {
            "name": "Dwarven Rune Stone",
            "description": "A stone with glowing runes",
            "money": 0,
            "items": [{"name": "Rune Stone", "quantity": 1, "value": 100}],
            "xp": {"magic": 20},
        },
        {
            "name": "Old Weapon",
            "description": "A well-preserved dwarven axe",
            "money": 0,
            "items": [{"name": "Dwarven Axe", "quantity": 1, "value": 80}],
        },
    ],
    "village": [
        {
            "name": "Fresh Vegetables",
            "description": "From a generous farmer",
            "money": 0,
            "items": [{"name": "Fresh Vegetables", "quantity": 3, "value": 5}],
        },
        {
            "name": "Herb Patch",
            "description": "Wild herbs growing near the village",
            "money": 0,
            "items": [{"name": "Healing Herbs", "quantity": 2, "value": 15}],
            "xp": {"healing": 10},
        },
        {
            "name": "Village Rumors",
            "description": "Local news and warnings",
            "money": 0,
            "xp": {"survival": 5, "negotiation": 5},
        },
    ],
    "shrine": [
        {
            "name": "Blessed Water",
            "description": "Water from the Moonwell",
            "money": 0,
            "items": [{"name": "Moonwell Water", "quantity": 1, "value": 40}],
            "xp": {"healing": 15},
        },
        {
            "name": "Meditation Insight",
            "description": "A moment of clarity",
            "money": 0,
            "xp": {"magic": 10, "healing": 10},
        },
        {
            "name": "Offering Left Behind",
            "description": "A small donation at the shrine",
            "money": 10,
            "xp": {},
        },
    ],
}


# Rest interruption events by time and location danger
REST_INTERRUPTIONS = {
    TimeOfDay.NIGHT: [
        {"description": "Wolves howl nearby, keeping you alert", "health_loss": 5},
        {"description": "Strange noises from the shadows", "health_loss": 3},
        {"description": "Cold wind seeps through your shelter", "health_loss": 2},
    ],
    TimeOfDay.EVENING: [
        {"description": "Rowdy travelers disturb your rest", "health_loss": 3},
        {"description": "Distant combat echoes through the night", "health_loss": 2},
    ],
}


async def get_available_activities(
    session: AsyncSession,
    character: Character,
    gameplay_state: GameplayState,
) -> dict:
    """Get available activities based on location and time."""
    current_location = None
    if gameplay_state.current_location_id:
        result = await session.execute(
            select(Location).where(Location.id == gameplay_state.current_location_id)
        )
        current_location = result.scalar_one_or_none()

    # Get location-based activities
    location_activities = (
        current_location.available_activities if current_location else []
    )

    # Get time-restricted activities
    from app.services.game.time import get_available_activities_for_time

    time_activities = get_available_activities_for_time(
        gameplay_state.current_time_of_day
    )

    # Intersection of both
    available = list(set(location_activities) & set(time_activities))

    return {
        "available_activities": available,
        "location_activities": location_activities,
        "time_restricted_activities": time_activities,
        "current_time_of_day": gameplay_state.current_time_of_day.value,
        "current_location_id": gameplay_state.current_location_id,
        "current_location_name": current_location.name if current_location else None,
    }


async def perform_explore(
    session: AsyncSession,
    character: Character,
    gameplay_state: GameplayState,
    location_id: int | None = None,
    rng_seed: int | None = None,
) -> dict:
    """Perform explore activity."""
    # Validate stamina BEFORE any side effects
    await _validate_stamina_for_activity(character, ActivityType.EXPLORE)

    rng = get_rng(rng_seed if rng_seed is not None else gameplay_state.session_id)

    # Determine location
    target_location_id = location_id or gameplay_state.current_location_id
    if not target_location_id:
        raise ValidationError(
            "No location to explore", details={"location_id": target_location_id}
        )

    location = await session.execute(
        select(Location).where(Location.id == target_location_id)
    )
    location = location.scalar_one_or_none()
    if not location:
        raise NotFoundError("Location", str(target_location_id))

    # Advance time
    time_cost = ACTIVITY_TIME_COSTS[ActivityType.EXPLORE]
    await advance_time(session, gameplay_state, time_cost)

    # Consume stamina and increase fatigue
    stamina_cost = ACTIVITY_STAMINA_COSTS[ActivityType.EXPLORE]
    fatigue_increase = ACTIVITY_FATIGUE_INCREASE[ActivityType.EXPLORE]
    await consume_stamina(session, character, stamina_cost)
    await increase_fatigue(session, character, fatigue_increase)

    # Determine discovery chance based on location danger and character attributes
    danger_modifier = {1: 0.8, 2: 0.6, 3: 0.4, 4: 0.2, 5: 0.1}.get(
        location.danger_level, 0.5
    )

    # Agility helps with exploration
    agility_attr = next(
        (a for a in character.attributes if a.name == AttributeName.AGILITY), None
    )
    agility_bonus = (agility_attr.current_value - 10) * 0.02 if agility_attr else 0

    discovery_chance = min(0.9, max(0.1, danger_modifier + agility_bonus + 0.3))

    discoveries = []
    encounters = []
    money_gained = 0
    xp_gained = {}
    items_gained = []

    if rng.random() < discovery_chance:
        # Successful discovery
        location_discoveries = EXPLORATION_DISCOVERIES.get(
            location.location_type, EXPLORATION_DISCOVERIES["city"]
        )
        discovery = rng.choice(location_discoveries)
        discoveries.append(discovery)

        money_gained += discovery.get("money", 0)
        for skill, xp in discovery.get("xp", {}).items():
            xp_gained[skill] = xp_gained.get(skill, 0) + xp
        for item in discovery.get("items", []):
            items_gained.append(item)
            # Add to inventory using new service
            await add_item(
                session,
                character,
                item["name"],
                item["quantity"],
                item.get("value", 0),
                item_type="consumable",
                description=f"Found while exploring {location.name}.",
            )
    else:
        # Nothing found, but maybe an encounter
        if rng.random() < 0.15 * location.danger_level / 5:
            encounters.append(
                {
                    "type": "minor_encounter",
                    "description": "You notice signs of recent activity but find nothing.",
                }
            )

    # Grant survival XP for exploring
    xp_gained["survival"] = xp_gained.get("survival", 0) + 5
    survival_xp_result = await grant_skill_xp(session, character, "survival", 5)

    # Grant character XP for exploring
    char_xp_result = await grant_character_xp(session, character, 10)

    # Apply money using new service
    if money_gained > 0:
        await add_money(session, character, money_gained)

    # Character progression info for response
    character_xp_gained = char_xp_result["xp_granted"]
    character_leveled_up = char_xp_result["leveled_up"]
    character_level = char_xp_result["new_level"]
    attribute_points_gained = char_xp_result["attribute_points_gained"]

    # Skill progression info for response
    skill_progression = {}
    for skill_name, xp in xp_gained.items():
        # Get the skill to check its current level
        result = await session.execute(
            select(CharacterSkill).where(
                CharacterSkill.character_id == character.id,
                CharacterSkill.name == SkillName(skill_name),
            )
        )
        skill = result.scalar_one_or_none()
        if skill:
            skill_progression[skill_name] = {
                "xp_gained": xp,
                "level": skill.level,
                "leveled_up": skill_name == "survival"
                and survival_xp_result["leveled_up"],
            }
        else:
            # New skill case
            skill_progression[skill_name] = {
                "xp_gained": xp,
                "level": 0,
                "leveled_up": False,
            }

    # Build narrative
    narrative_parts = [f"You explore {location.name}."]
    if char_xp_result["leveled_up"]:
        narrative_parts.append(
            f" You have reached level {char_xp_result['new_level']}!"
        )
    if survival_xp_result["leveled_up"]:
        narrative_parts.append(
            f" Your survival skill has reached level {survival_xp_result['new_level']}!"
        )
    if discoveries:
        d = discoveries[0]
        narrative_parts.append(f"You discover: {d['description']}.")
        if d.get("money", 0) > 0:
            narrative_parts.append(f"Found {d['money']} gold.")
        if d.get("items"):
            for item in d["items"]:
                narrative_parts.append(f"Found {item['name']}.")
    else:
        narrative_parts.append("You find nothing of interest this time.")

    if encounters:
        for enc in encounters:
            narrative_parts.append(f"Encounter: {enc['description']}")

    narrative = " ".join(narrative_parts)

    # Log activity
    gameplay_state.recent_activities.append(
        {
            "type": "explore",
            "location_id": target_location_id,
            "discoveries": len(discoveries),
            "money_gained": money_gained,
            "day": gameplay_state.current_day,
            "time_of_day": gameplay_state.current_time_of_day.value,
        }
    )
    if len(gameplay_state.recent_activities) > 20:
        gameplay_state.recent_activities = gameplay_state.recent_activities[-20:]

    await session.flush()

    # Apply condition effects after activity
    condition_effects = await apply_condition_effects(session, character)

    return {
        "result": {
            "success": True,
            "message": "Exploration complete",
            "time_advanced": time_cost,
            "health_change": condition_effects["health_change"],
            "money_change": money_gained,
            "experience_gained": xp_gained,
            "character_xp_gained": character_xp_gained,
            "character_leveled_up": character_leveled_up,
            "character_level": character_level,
            "attribute_points_gained": attribute_points_gained,
            "skill_progression": skill_progression,
            "items_gained": items_gained,
            "items_lost": [],
            "new_time_of_day": gameplay_state.current_time_of_day.value,
            "new_day": gameplay_state.current_day,
            "narrative": narrative,
            "stamina_change": -stamina_cost,
            "fatigue_change": fatigue_increase,
            "died": condition_effects.get("died", False),
        },
        "discoveries": discoveries,
        "encounters": encounters,
    }


async def perform_rest(
    session: AsyncSession,
    character: Character,
    gameplay_state: GameplayState,
    duration: str = "long",
    rng_seed: int | None = None,
) -> dict:
    """Perform rest activity."""
    rng = get_rng(rng_seed if rng_seed is not None else gameplay_state.session_id)

    # Determine time cost and health restore
    if duration == "short":
        time_cost = ACTIVITY_TIME_COSTS[ActivityType.REST_SHORT]
        base_heal = 15
    else:
        time_cost = ACTIVITY_TIME_COSTS[ActivityType.REST]
        base_heal = 30

    # Vitality modifier
    vitality_attr = next(
        (a for a in character.attributes if a.name == AttributeName.VITALITY), None
    )
    vitality_bonus = (vitality_attr.current_value - 10) * 2 if vitality_attr else 0
    total_heal = min(
        character.max_health - character.current_health, base_heal + vitality_bonus
    )

    # Check for interruption
    was_interrupted = False
    interruption_event = None
    health_loss = 0

    if duration == "long" and gameplay_state.current_time_of_day in (
        TimeOfDay.NIGHT,
        TimeOfDay.EVENING,
    ):
        # Chance of interruption based on location danger
        location = None
        if gameplay_state.current_location_id:
            result = await session.execute(
                select(Location).where(
                    Location.id == gameplay_state.current_location_id
                )
            )
            location = result.scalar_one_or_none()

        danger = location.danger_level if location else 2
        interruption_chance = {1: 0.05, 2: 0.1, 3: 0.2, 4: 0.35, 5: 0.5}.get(
            danger, 0.1
        )

        if rng.random() < interruption_chance:
            was_interrupted = True
            interruptions = REST_INTERRUPTIONS.get(
                gameplay_state.current_time_of_day,
                REST_INTERRUPTIONS[TimeOfDay.EVENING],
            )
            interruption_event = rng.choice(interruptions)
            health_loss = interruption_event["health_loss"]
            total_heal = max(0, total_heal - health_loss)

    # Apply healing
    character.current_health = min(
        character.max_health, character.current_health + total_heal
    )

    # Advance time
    await advance_time(session, gameplay_state, time_cost)

    # Restore stamina and reduce fatigue
    activity_type = ActivityType.REST if duration == "long" else ActivityType.REST_SHORT
    stamina_restore = 30 if duration == "long" else 15  # Rest restores stamina
    fatigue_reduction = -ACTIVITY_FATIGUE_INCREASE[
        activity_type
    ]  # Negative = reduction

    await restore_stamina(session, character, stamina_restore)
    await reduce_fatigue(session, character, fatigue_reduction)

    # Build narrative
    if was_interrupted:
        narrative = f"You attempt to rest, but {interruption_event['description'].lower()}. You recover {total_heal} health."
    else:
        narrative = f"You rest {'briefly' if duration == 'short' else 'soundly'} and recover {total_heal} health."

    # Log activity
    gameplay_state.recent_activities.append(
        {
            "type": "rest",
            "duration": duration,
            "health_restored": total_heal,
            "was_interrupted": was_interrupted,
            "day": gameplay_state.current_day,
            "time_of_day": gameplay_state.current_time_of_day.value,
        }
    )
    if len(gameplay_state.recent_activities) > 20:
        gameplay_state.recent_activities = gameplay_state.recent_activities[-20:]

    # Apply condition effects after activity
    condition_effects = await apply_condition_effects(session, character)

    await session.flush()

    return {
        "result": {
            "success": True,
            "message": "Rest complete",
            "time_advanced": time_cost,
            "health_change": total_heal + condition_effects["health_change"],
            "money_change": 0,
            "experience_gained": {},
            "items_gained": [],
            "items_lost": [],
            "new_time_of_day": gameplay_state.current_time_of_day.value,
            "new_day": gameplay_state.current_day,
            "narrative": narrative,
            "stamina_change": stamina_restore,
            "fatigue_change": -fatigue_reduction,
            "died": condition_effects.get("died", False),
        },
        "health_restored": total_heal,
        "was_interrupted": was_interrupted,
        "interruption_event": interruption_event,
    }


async def perform_work(
    session: AsyncSession,
    character: Character,
    gameplay_state: GameplayState,
    work_type: str | None = None,
    rng_seed: int | None = None,
) -> dict:
    """Perform work activity."""
    # Validate stamina BEFORE any side effects
    await _validate_stamina_for_activity(character, ActivityType.WORK)

    rng = get_rng(rng_seed if rng_seed is not None else gameplay_state.session_id)

    # Get current location
    if not gameplay_state.current_location_id:
        raise ValidationError("Must be at a location to work")

    location = await session.execute(
        select(Location).where(Location.id == gameplay_state.current_location_id)
    )
    location = location.scalar_one_or_none()
    if not location:
        raise NotFoundError("Location", str(gameplay_state.current_location_id))

    # Get available work types for this location
    available_work = WORK_TYPES.get(location.location_type, WORK_TYPES["city"])

    # Select work type
    if work_type:
        selected_work = next(
            (w for w in available_work if w["name"].lower() == work_type.lower()), None
        )
        if not selected_work:
            raise ValidationError(
                f"Work type '{work_type}' not available at this location",
                details={"available": [w["name"] for w in available_work]},
            )
    else:
        selected_work = rng.choice(available_work)

    # Calculate wages based on relevant attribute and skill
    skill_name = selected_work["skill"]
    attr_name = selected_work["attr"]

    # Get attribute value
    attr_enum = getattr(AttributeName, attr_name.upper(), None)
    attr_value = 10
    if attr_enum:
        attr = next((a for a in character.attributes if a.name == attr_enum), None)
        if attr:
            attr_value = attr.current_value

    # Get skill level
    skill_enum = getattr(SkillName, skill_name.upper(), None)
    skill_level = 0
    if skill_enum:
        skill = next((s for s in character.skills if s.name == skill_enum), None)
        if skill:
            skill_level = skill.level

    # Base wages + attribute bonus + skill bonus
    base_money = selected_work["base_money"]
    attr_bonus = (attr_value - 10) * 2
    skill_bonus = skill_level * 3
    # Random variation
    variation = rng.randint(-3, 5)

    wages = max(1, base_money + attr_bonus + skill_bonus + variation)

    # Grant skill XP
    xp_gained = 10 + skill_level * 2
    skill_xp_result = await grant_skill_xp(session, character, skill_name, xp_gained)

    # Grant character XP for working
    char_xp_result = await grant_character_xp(session, character, 15)
    character_xp_gained = char_xp_result["xp_granted"]
    character_leveled_up = char_xp_result["leveled_up"]
    character_level = char_xp_result["new_level"]
    attribute_points_gained = char_xp_result["attribute_points_gained"]

    # Skill progression info for response
    skill_progression = {}
    if skill_xp_result:
        skill_progression[skill_name] = {
            "xp_gained": xp_gained,
            "level": skill_xp_result["new_level"],
            "leveled_up": skill_xp_result["leveled_up"],
        }

    # Apply wages using new service
    await add_money(session, character, wages)

    # Advance time
    time_cost = ACTIVITY_TIME_COSTS[ActivityType.WORK]
    await advance_time(session, gameplay_state, time_cost)

    # Consume stamina and increase fatigue
    stamina_cost = ACTIVITY_STAMINA_COSTS[ActivityType.WORK]
    fatigue_increase = ACTIVITY_FATIGUE_INCREASE[ActivityType.WORK]
    await consume_stamina(session, character, stamina_cost)
    await increase_fatigue(session, character, fatigue_increase)

    # Build narrative
    if character_leveled_up and skill_xp_result["leveled_up"]:
        narrative = f"You work as a {selected_work['name']}: {selected_work['description']}. You earn {wages} gold and gain {xp_gained} {skill_name} experience. You have reached level {character_level} and your {skill_name} skill has reached level {skill_xp_result['new_level']}!"
    elif character_leveled_up:
        narrative = f"You work as a {selected_work['name']}: {selected_work['description']}. You earn {wages} gold and gain {xp_gained} {skill_name} experience. You have reached level {character_level}!"
    elif skill_xp_result["leveled_up"]:
        narrative = f"You work as a {selected_work['name']}: {selected_work['description']}. You earn {wages} gold and gain {xp_gained} {skill_name} experience. Your {skill_name} skill has reached level {skill_xp_result['new_level']}!"
    else:
        narrative = f"You work as a {selected_work['name']}: {selected_work['description']}. You earn {wages} gold and gain {xp_gained} {skill_name} experience."

    # Log activity
    gameplay_state.recent_activities.append(
        {
            "type": "work",
            "work_type": selected_work["name"],
            "wages": wages,
            "skill_xp": xp_gained,
            "day": gameplay_state.current_day,
            "time_of_day": gameplay_state.current_time_of_day.value,
        }
    )
    if len(gameplay_state.recent_activities) > 20:
        gameplay_state.recent_activities = gameplay_state.recent_activities[-20:]

    # Apply condition effects after activity
    condition_effects = await apply_condition_effects(session, character)

    await session.flush()

    return {
        "result": {
            "success": True,
            "message": "Work complete",
            "time_advanced": time_cost,
            "health_change": condition_effects["health_change"],
            "money_change": wages,
            "experience_gained": {skill_name: xp_gained},
            "character_xp_gained": character_xp_gained,
            "character_leveled_up": character_leveled_up,
            "character_level": character_level,
            "attribute_points_gained": attribute_points_gained,
            "skill_progression": skill_progression,
            "items_gained": [],
            "items_lost": [],
            "new_time_of_day": gameplay_state.current_time_of_day.value,
            "new_day": gameplay_state.current_day,
            "narrative": narrative,
            "stamina_change": -stamina_cost,
            "fatigue_change": fatigue_increase,
            "died": condition_effects.get("died", False),
        },
        "work_performed": selected_work["name"],
        "wages_earned": wages,
    }


async def _add_item_to_inventory(
    session: AsyncSession,
    character: Character,
    item_name: str,
    quantity: int,
    value: int,
) -> InventoryItem:
    """Add item to character inventory."""
    # Check if item already exists
    result = await session.execute(
        select(InventoryItem).where(
            InventoryItem.character_id == character.id,
            InventoryItem.name == item_name,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.quantity += quantity
        await session.flush()
        return existing

    # Create new item
    item_id = item_name.lower().replace(" ", "_").replace("'", "").replace(",", "")
    new_item = InventoryItem(
        character_id=character.id,
        item_id=item_id,
        name=item_name,
        description="Acquired during activity.",
        quantity=quantity,
        item_type="misc",
        value=value,
        is_equipped=False,
        properties={},
    )
    session.add(new_item)
    await session.flush()
    return new_item


async def _grant_skill_xp(
    session: AsyncSession,
    character: Character,
    skill_name: str,
    xp: int,
):
    """Grant XP to a skill."""
    try:
        skill_enum = SkillName(skill_name)
    except ValueError:
        return

    result = await session.execute(
        select(CharacterSkill).where(
            CharacterSkill.character_id == character.id,
            CharacterSkill.name == skill_enum,
        )
    )
    skill = result.scalar_one_or_none()

    if skill:
        skill.experience += xp
        # Check for level up
        while skill.experience >= skill.experience_for_next_level:
            skill.experience -= skill.experience_for_next_level
            skill.level += 1
    else:
        # Create new skill at level 0 with XP
        skill = CharacterSkill(
            character_id=character.id,
            name=skill_enum,
            level=0,
            experience=xp,
        )
        session.add(skill)

    await session.flush()
