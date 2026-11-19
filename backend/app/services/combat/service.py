"""Authoritative domain service for the Combat System.

Implements lightweight turn-based combat encounters, initiative rolls (Agility + 1d20),
player actions (attack, defend, use_skill, use_item, flee), enemy AI, damage formulas,
victory rewards (XP, gold, loot), and combat fatality handling per SPEC.md §8 & AGENTS.md.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.exceptions import GameStateError, NotFoundError, ValidationError
from app.core.rng import get_rng
from app.models.enums import AttributeName, DeathCause, EnemyType, SkillName
from app.models.gameplay import (
    Character,
    CharacterAttribute,
    CharacterSkill,
    GameplayState,
    InventoryItem,
)
from app.models.world import Enemy
from app.services.character.progression import grant_character_xp, grant_skill_xp
from app.services.reincarnation.death import record_death


async def _get_character_combat_stats(
    session: AsyncSession, character_id: int
) -> dict[str, int]:
    """Retrieve effective combat attributes and skill levels for a character."""
    attr_res = await session.execute(
        select(CharacterAttribute).where(
            CharacterAttribute.character_id == character_id
        )
    )
    attributes = {attr.name: attr.current_value for attr in attr_res.scalars().all()}

    skill_res = await session.execute(
        select(CharacterSkill).where(CharacterSkill.character_id == character_id)
    )
    skills = {skill.name: skill.level for skill in skill_res.scalars().all()}

    str_val = attributes.get(AttributeName.STRENGTH, 10)
    agi_val = attributes.get(AttributeName.AGILITY, 10)
    vit_val = attributes.get(AttributeName.VITALITY, 10)
    int_val = attributes.get(AttributeName.INTELLIGENCE, 10)

    # Combat skill is the highest of swordsmanship, archery, or magic
    combat_skill = max(
        skills.get(SkillName.SWORDSMANSHIP, 0),
        skills.get(SkillName.ARCHERY, 0),
        skills.get(SkillName.MAGIC, 0),
    )

    return {
        "strength": str_val,
        "agility": agi_val,
        "vitality": vit_val,
        "intelligence": int_val,
        "defense": max(1, vit_val // 3),
        "combat_skill": combat_skill,
    }


async def start_combat(
    session: AsyncSession,
    character_id: int,
    enemy_type: Optional[str] = None,
    rng_seed: Optional[int] = None,
) -> dict[str, Any]:
    """Initiate a combat encounter.

    Authoritative: checks character status, rolls initiative, sets GameplayState.in_combat,
    initializes combat_state JSON, and flushes to database.
    """
    # 1. Load character
    char = await session.get(Character, character_id)
    if char is None:
        raise NotFoundError("Character", character_id)
    if not char.is_alive:
        raise GameStateError("Deceased characters cannot enter combat.")

    # 2. Load GameplayState
    state_res = await session.execute(
        select(GameplayState).where(GameplayState.character_id == character_id)
    )
    gameplay_state = state_res.scalar_one_or_none()
    if gameplay_state is None:
        raise NotFoundError("GameplayState for character", character_id)

    # Return existing active combat if already engaged
    if (
        gameplay_state.in_combat
        and gameplay_state.combat_state.get("status") == "active"
    ):
        return _format_combat_state_response(char, gameplay_state.combat_state)

    # 3. Load or select enemy
    if enemy_type:
        try:
            enemy_enum = EnemyType(enemy_type)
        except ValueError:
            raise ValidationError(f"Invalid enemy type: '{enemy_type}'.")
        enemy_res = await session.execute(select(Enemy).where(Enemy.name == enemy_enum))
        enemy = enemy_res.scalar_one_or_none()
        if enemy is None:
            raise NotFoundError("Enemy", enemy_type)
    else:
        enemies_res = await session.execute(select(Enemy).order_by(Enemy.id))
        all_enemies = list(enemies_res.scalars().all())
        if not all_enemies:
            raise NotFoundError("Enemy", "any available")
        # Deterministic selection
        rng = get_rng(rng_seed or char.session_id)
        enemy = rng.choice(all_enemies)

    # 4. Roll Initiative: Agility + 1d20 per AGENTS.md §14 Recommendation 5
    char_stats = await _get_character_combat_stats(session, character_id)
    rng = get_rng(rng_seed or char.session_id)

    player_d20 = rng.randint(1, 20)
    enemy_d20 = rng.randint(1, 20)
    player_initiative = char_stats["agility"] + player_d20
    enemy_initiative = enemy.base_agility + enemy_d20
    player_first = player_initiative >= enemy_initiative

    # 5. Build initial combat state
    combat_state: dict[str, Any] = {
        "enemy": {
            "id": enemy.id,
            "name": enemy.name.value,
            "display_name": enemy.display_name,
            "description": enemy.description,
            "current_health": enemy.base_health,
            "max_health": enemy.base_health,
            "attack": enemy.base_attack,
            "defense": enemy.base_defense,
            "agility": enemy.base_agility,
            "experience_reward": enemy.experience_reward,
            "money_min": enemy.money_reward_min,
            "money_max": enemy.money_reward_max,
            "possible_loot": enemy.possible_loot or [],
        },
        "turn": 1,
        "player_first": player_first,
        "player_defending": False,
        "status": "active",
        "log": [
            f"You encounter a dangerous {enemy.display_name}!",
            (
                f"Initiative: You rolled {player_initiative} ({char_stats['agility']} agi + {player_d20}) "
                f"vs Enemy {enemy_initiative}. You act first!"
                if player_first
                else f"Initiative: You rolled {player_initiative} vs Enemy {enemy_initiative}. The enemy strikes first!"
            ),
        ],
    }

    gameplay_state.in_combat = True
    gameplay_state.combat_enemy_id = enemy.id
    gameplay_state.combat_state = combat_state

    await session.flush()
    return _format_combat_state_response(char, combat_state)


async def get_combat_state(session: AsyncSession, character_id: int) -> dict[str, Any]:
    """Retrieve the active combat state for a character."""
    char = await session.get(Character, character_id)
    if char is None:
        raise NotFoundError("Character", character_id)

    state_res = await session.execute(
        select(GameplayState).where(GameplayState.character_id == character_id)
    )
    gameplay_state = state_res.scalar_one_or_none()
    if gameplay_state is None or not gameplay_state.in_combat:
        return {
            "in_combat": False,
            "turn": 0,
            "status": "none",
            "log": [],
            "available_actions": [],
        }

    return _format_combat_state_response(char, gameplay_state.combat_state)


async def execute_combat_turn(
    session: AsyncSession,
    character_id: int,
    action: str,
    skill_name: Optional[str] = None,
    item_name: Optional[str] = None,
    rng_seed: Optional[int] = None,
) -> dict[str, Any]:
    """Process a single turn of combat for the character.

    Authoritative: updates health, stamina, inventory, awards victory XP/gold/loot,
    handles character defeat and death records, flushes state to database.
    """
    # 1. Load character
    char = await session.get(Character, character_id)
    if char is None:
        raise NotFoundError("Character", character_id)
    if not char.is_alive:
        raise GameStateError("Deceased characters cannot take combat actions.")

    # 2. Load GameplayState
    state_res = await session.execute(
        select(GameplayState).where(GameplayState.character_id == character_id)
    )
    gameplay_state = state_res.scalar_one_or_none()
    if (
        gameplay_state is None
        or not gameplay_state.in_combat
        or gameplay_state.combat_state.get("status") != "active"
    ):
        raise GameStateError("Character is not currently in active combat.")

    valid_actions = {"attack", "defend", "use_skill", "use_item", "flee"}
    if action.lower() not in valid_actions:
        raise ValidationError(
            f"Invalid action '{action}'. Valid actions: {sorted(valid_actions)}."
        )

    combat_state = dict(gameplay_state.combat_state)
    enemy_data = combat_state["enemy"]
    char_stats = await _get_character_combat_stats(session, character_id)
    rng = get_rng(rng_seed or char.session_id)

    turn_logs: list[str] = []
    player_damage = 0
    enemy_damage = 0
    victory_rewards: Optional[dict[str, Any]] = None
    death_cause: Optional[str] = None
    action = action.lower()

    # =========================================================================
    # ACTION: FLEE / ESCAPE
    # =========================================================================
    if action == "flee":
        escape_dc = enemy_data["agility"] + 10
        flee_roll = char_stats["agility"] + rng.randint(1, 20)
        if flee_roll >= escape_dc:
            combat_state["status"] = "fled"
            gameplay_state.in_combat = False
            turn_logs.append(
                f"You sprint away and break line of sight (rolled {flee_roll} vs DC {escape_dc}). "
                "You successfully escaped from combat!"
            )
            combat_state["log"].extend(turn_logs)
            gameplay_state.combat_state = combat_state
            await session.flush()
            return _format_action_response(
                char, combat_state, player_damage, enemy_damage, turn_logs
            )
        else:
            turn_logs.append(
                f"You failed to escape (rolled {flee_roll} vs DC {escape_dc})! "
                f"The {enemy_data['display_name']} lunges as you turn!"
            )

    # =========================================================================
    # ACTION: DEFEND
    # =========================================================================
    elif action == "defend":
        combat_state["player_defending"] = True
        stamina_recovered = 5
        char.current_stamina = min(
            char.max_stamina, char.current_stamina + stamina_recovered
        )
        turn_logs.append(
            f"You brace yourself in a defensive stance, recovering {stamina_recovered} stamina. "
            "Incoming damage will be reduced by 50%!"
        )

    # =========================================================================
    # ACTION: USE ITEM
    # =========================================================================
    elif action == "use_item":
        if not item_name:
            raise ValidationError("Item name must be specified for use_item action.")

        item_res = await session.execute(
            select(InventoryItem).where(
                InventoryItem.character_id == character_id,
                InventoryItem.name == item_name,
            )
        )
        inv_item = item_res.scalar_one_or_none()
        if inv_item is None or inv_item.quantity < 1:
            raise ValidationError(f"Item '{item_name}' is not in character inventory.")

        # Consume 1 item
        if inv_item.quantity > 1:
            inv_item.quantity -= 1
        else:
            await session.delete(inv_item)

        heal_amount = max(25, inv_item.value)
        char.current_health = min(char.max_health, char.current_health + heal_amount)
        turn_logs.append(
            f"You consumed {item_name}, restoring {heal_amount} health! "
            f"(HP: {char.current_health}/{char.max_health})"
        )

    # =========================================================================
    # ACTION: USE SKILL
    # =========================================================================
    elif action == "use_skill":
        stamina_cost = 15
        if char.current_stamina < stamina_cost:
            raise ValidationError(
                f"Insufficient stamina to use skill: needs {stamina_cost}, has {char.current_stamina}."
            )
        char.current_stamina -= stamina_cost

        # Calculate high-powered skill attack
        hit_d20 = rng.randint(1, 20)
        base_dmg = int(
            1.5 * (char_stats["strength"] // 2 + char_stats["combat_skill"] * 2 + 5)
        )
        dmg = max(3, base_dmg + hit_d20 // 4 - enemy_data["defense"])
        enemy_data["current_health"] = max(0, enemy_data["current_health"] - dmg)
        player_damage = dmg
        skill_display = skill_name.title() if skill_name else "Special Technique"
        turn_logs.append(
            f"You unleash a devastating {skill_display}! "
            f"Dealt {dmg} damage to {enemy_data['display_name']}! "
            f"(Enemy HP: {enemy_data['current_health']}/{enemy_data['max_health']})"
        )

    # =========================================================================
    # ACTION: ATTACK
    # =========================================================================
    elif action == "attack":
        stamina_cost = 5
        if char.current_stamina >= stamina_cost:
            char.current_stamina -= stamina_cost
            stamina_factor = 1.0
        else:
            stamina_factor = 0.5  # Fatigued penalty

        hit_d20 = rng.randint(1, 20)
        is_crit = hit_d20 == 20
        base_dmg = int(
            (
                char_stats["strength"] // 2
                + char_stats["combat_skill"] * 2
                + hit_d20 // 4
            )
            * stamina_factor
        )
        dmg = max(1, base_dmg - enemy_data["defense"])
        if is_crit:
            dmg = int(dmg * 1.5)

        enemy_data["current_health"] = max(0, enemy_data["current_health"] - dmg)
        player_damage = dmg
        turn_logs.append(
            f"You strike the {enemy_data['display_name']}"
            f"{' (CRITICAL HIT!)' if is_crit else ''} for {dmg} damage! "
            f"(Enemy HP: {enemy_data['current_health']}/{enemy_data['max_health']})"
        )

    # =========================================================================
    # RESOLUTION: ENEMY DEFEATED (VICTORY)
    # =========================================================================
    if enemy_data["current_health"] <= 0:
        combat_state["status"] = "victory"
        gameplay_state.in_combat = False

        # Award rewards
        xp_gain = enemy_data.get("experience_reward", 20)
        gold_min = enemy_data.get("money_min", 2)
        gold_max = enemy_data.get("money_max", 15)
        gold_gain = rng.randint(gold_min, gold_max)

        # Roll loot
        possible_loot = enemy_data.get("possible_loot", [])
        loot_gained: list[str] = []
        if possible_loot and rng.random() < 0.5:
            loot_name = rng.choice(possible_loot)
            loot_gained.append(loot_name)
            # Add to inventory
            item_res = await session.execute(
                select(InventoryItem).where(
                    InventoryItem.character_id == character_id,
                    InventoryItem.name == loot_name,
                )
            )
            existing_item = item_res.scalar_one_or_none()
            if existing_item:
                existing_item.quantity += 1
            else:
                new_item = InventoryItem(
                    character_id=character_id,
                    item_id=loot_name.lower().replace(" ", "_"),
                    name=loot_name,
                    description=f"Loot recovered from {enemy_data['display_name']}",
                    quantity=1,
                    item_type="material",
                    value=10,
                )
                session.add(new_item)

        # Apply character & skill progression
        char.money += gold_gain
        await grant_character_xp(session, char, xp_gain)
        await grant_skill_xp(session, char, SkillName.SWORDSMANSHIP, xp_gain // 2)

        victory_rewards = {
            "xp_gained": xp_gain,
            "gold_gained": gold_gain,
            "loot_gained": loot_gained,
            "skill_xp_gained": {"swordsmanship": xp_gain // 2},
        }

        turn_logs.append(
            f"The {enemy_data['display_name']} falls motionless! Victory! "
            f"Gained {xp_gain} XP, {gold_gain} gold."
            + (f" Recovered loot: {', '.join(loot_gained)}." if loot_gained else "")
        )

        combat_state["log"].extend(turn_logs)
        gameplay_state.combat_state = combat_state
        flag_modified(gameplay_state, "combat_state")
        await session.flush()
        return _format_action_response(
            char,
            combat_state,
            player_damage,
            enemy_damage,
            turn_logs,
            victory_rewards=victory_rewards,
        )

    # =========================================================================
    # ENEMY COUNTER-ATTACK (IF ENEMY STILL ALIVE & NOT FLED)
    # =========================================================================
    if combat_state["status"] == "active":
        enemy_atk_roll = rng.randint(1, 6)
        raw_enemy_dmg = enemy_data["attack"] + enemy_atk_roll - char_stats["defense"]

        # Player defend status reduces damage by 50%
        if combat_state.get("player_defending", False):
            raw_enemy_dmg = raw_enemy_dmg // 2
            combat_state["player_defending"] = (
                False  # Guard expires after absorbing hit
            )

        final_enemy_dmg = max(1, raw_enemy_dmg)
        char.current_health = max(0, char.current_health - final_enemy_dmg)
        enemy_damage = final_enemy_dmg
        turn_logs.append(
            f"The {enemy_data['display_name']} lashes out, dealing {final_enemy_dmg} damage! "
            f"(Player HP: {char.current_health}/{char.max_health})"
        )

        # =====================================================================
        # RESOLUTION: PLAYER SLAIN (DEFEAT)
        # =====================================================================
        if char.current_health <= 0:
            combat_state["status"] = "defeat"
            gameplay_state.in_combat = False

            char.is_alive = False
            char.died_at = datetime.now(timezone.utc)
            char.death_cause = DeathCause.COMBAT
            char.death_description = (
                f"Slain in fierce battle by a {enemy_data['display_name']}."
            )
            char.age_at_death = char.age
            death_cause = DeathCause.COMBAT.value

            turn_logs.append(
                f"Your wounds are too severe... You have been slain by the {enemy_data['display_name']}!"
            )
            await record_death(
                session=session,
                character_id=char.id,
                cause=DeathCause.COMBAT,
                death_description=char.death_description,
            )

    combat_state["turn"] += 1
    combat_state["log"].extend(turn_logs)
    gameplay_state.combat_state = combat_state
    flag_modified(gameplay_state, "combat_state")

    await session.flush()
    return _format_action_response(
        char,
        combat_state,
        player_damage,
        enemy_damage,
        turn_logs,
        victory_rewards=victory_rewards,
        death_cause=death_cause,
    )


def _format_combat_state_response(
    char: Character, combat_state: dict[str, Any]
) -> dict[str, Any]:
    """Format combat state dictionary into a clean response."""
    enemy_data = combat_state.get("enemy")
    enemy_schema = None
    if enemy_data:
        enemy_schema = {
            "id": enemy_data["id"],
            "name": enemy_data["name"],
            "display_name": enemy_data["display_name"],
            "description": enemy_data["description"],
            "current_health": enemy_data["current_health"],
            "max_health": enemy_data["max_health"],
            "attack": enemy_data["attack"],
            "defense": enemy_data["defense"],
            "agility": enemy_data["agility"],
        }

    player_schema = {
        "character_id": char.id,
        "name": char.name,
        "current_health": char.current_health,
        "max_health": char.max_health,
        "current_stamina": char.current_stamina,
        "max_stamina": char.max_stamina,
        "is_defending": combat_state.get("player_defending", False),
    }

    return {
        "in_combat": combat_state.get("status") == "active",
        "turn": combat_state.get("turn", 1),
        "status": combat_state.get("status", "active"),
        "player_first": combat_state.get("player_first", True),
        "enemy": enemy_schema,
        "player": player_schema,
        "log": combat_state.get("log", []),
        "available_actions": ["attack", "defend", "use_skill", "use_item", "flee"],
    }


def _format_action_response(
    char: Character,
    combat_state: dict[str, Any],
    player_damage: int,
    enemy_damage: int,
    turn_logs: list[str],
    victory_rewards: Optional[dict[str, Any]] = None,
    death_cause: Optional[str] = None,
) -> dict[str, Any]:
    """Format turn action outcome into response."""
    state_res = _format_combat_state_response(char, combat_state)
    return {
        "in_combat": state_res["in_combat"],
        "status": combat_state.get("status", "active"),
        "turn": combat_state.get("turn", 1),
        "player_damage_dealt": player_damage,
        "enemy_damage_dealt": enemy_damage,
        "player": state_res["player"],
        "enemy": state_res["enemy"],
        "log_entries": turn_logs,
        "victory_rewards": victory_rewards,
        "death_cause": death_cause,
    }
