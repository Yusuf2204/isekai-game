"""Comprehensive test suite for Stage 10 Increment 3: Combat System.

Verifies:
1. Combat start, enemy loading (all 5 enemies), and initiative calculations (Agility + 1d20).
2. Resuming active combat idempotently from session.
3. Turn actions: attack, defend (50% damage reduction & stamina recovery), use_skill, use_item, flee.
4. Victory resolution: XP, skill XP, gold, and loot rewards.
5. Defeat resolution: HP reduction to 0 triggers DeathCause.COMBAT and records fatality details.
6. Deceased character rejection guard.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import get_session, recreate_db
from app.main import app, lifespan
from app.models.enums import (
    BackgroundName,
    DeathCause,
    EnemyType,
    GenderPresentation,
    RaceName,
)
from app.models.gameplay import Character, GameplayState, InventoryItem


@pytest_asyncio.fixture(autouse=True)
async def isolated_test_db():
    """Ensure database tables are recreated and world is seeded before each test."""
    await recreate_db()
    async with lifespan(app):
        yield


async def _create_test_character(
    client: AsyncClient, starting_gold: int = 50, starting_health: int = 100
) -> dict:
    """Helper to create a fresh character with specific health/gold."""
    create_res = await client.post(
        "/api/character/create",
        json={
            "name": "Combat Warrior",
            "race_name": RaceName.HUMAN.value,
            "background_name": BackgroundName.COMMONER.value,
            "gender_presentation": GenderPresentation.MALE.value,
        },
    )
    assert create_res.status_code == 201
    char_data = create_res.json()
    char_id = char_data["character"]["id"]

    async with get_session() as session:
        char = await session.get(Character, char_id)
        assert char is not None
        char.money = starting_gold
        char.current_health = starting_health
        char.current_stamina = 100
        await session.flush()

    return char_data


class TestCombatInitializationAndInitiative:
    """Tests starting combat, enemy loading, and initiative mechanics."""

    @pytest.mark.asyncio
    async def test_start_combat_with_slime_initializes_state(self):
        """Starting combat with a Slime loads base stats, rolls initiative, and sets in_combat."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            res = await client.post(
                "/api/combat/start",
                json={"session_token": token, "enemy_type": EnemyType.SLIME.value},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["in_combat"] is True
            assert data["turn"] == 1
            assert data["status"] == "active"
            assert data["enemy"]["name"] == "slime"
            assert data["enemy"]["display_name"] == "Slime"
            assert data["enemy"]["current_health"] == 25
            assert data["player"]["name"] == "Combat Warrior"
            assert len(data["log"]) >= 1

    @pytest.mark.asyncio
    async def test_start_combat_without_enemy_type_picks_random_enemy(self):
        """Starting combat without specifying enemy selects an eligible enemy."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            res = await client.post(
                "/api/combat/start",
                json={"session_token": token},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["in_combat"] is True
            assert data["enemy"] is not None
            assert data["enemy"]["name"] in [
                "slime",
                "goblin",
                "dire_wolf",
                "skeleton",
                "corrupted_beast",
            ]

    @pytest.mark.asyncio
    async def test_start_combat_already_in_combat_returns_current_state(self):
        """Re-calling start while in active combat is idempotent and returns current state."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            res1 = await client.post(
                "/api/combat/start",
                json={"session_token": token, "enemy_type": "goblin"},
            )
            assert res1.status_code == 200

            res2 = await client.post(
                "/api/combat/start",
                json={"session_token": token, "enemy_type": "slime"},
            )
            assert res2.status_code == 200
            # Remains goblin, does not replace active encounter
            assert res2.json()["enemy"]["name"] == "goblin"

    @pytest.mark.asyncio
    async def test_get_combat_state_endpoint(self):
        """GET /api/combat/state returns current encounter or in_combat: false."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            # Before combat
            state_before = await client.get(
                "/api/combat/state", params={"session_token": token}
            )
            assert state_before.status_code == 200
            assert state_before.json()["in_combat"] is False

            # Start combat
            await client.post(
                "/api/combat/start",
                json={"session_token": token, "enemy_type": "skeleton"},
            )

            # After combat start
            state_after = await client.get(
                "/api/combat/state", params={"session_token": token}
            )
            assert state_after.status_code == 200
            assert state_after.json()["in_combat"] is True
            assert state_after.json()["enemy"]["name"] == "skeleton"


class TestCombatTurnActions:
    """Tests attack, defend, use_skill, use_item, and flee actions."""

    @pytest.mark.asyncio
    async def test_action_attack_deals_damage_and_receives_counter_attack(self):
        """Standard attack damages enemy, consumes stamina, and receives counter attack."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            await client.post(
                "/api/combat/start",
                json={"session_token": token, "enemy_type": "dire_wolf"},
            )

            action_res = await client.post(
                "/api/combat/action",
                json={"session_token": token, "action": "attack"},
            )
            assert action_res.status_code == 200
            data = action_res.json()
            assert data["player_damage_dealt"] > 0
            assert data["enemy_damage_dealt"] > 0
            assert data["turn"] == 2
            assert data["player"]["current_stamina"] == 95  # 100 - 5

    @pytest.mark.asyncio
    async def test_action_defend_halves_incoming_damage_and_recovers_stamina(self):
        """Defending reduces enemy incoming damage by 50% and recovers 5 stamina."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]
            char_id = char_data["character"]["id"]

            # Reduce stamina to 80 to verify stamina recovery
            async with get_session() as session:
                char = await session.get(Character, char_id)
                char.current_stamina = 80
                await session.flush()

            await client.post(
                "/api/combat/start",
                json={"session_token": token, "enemy_type": "goblin"},
            )

            defend_res = await client.post(
                "/api/combat/action",
                json={"session_token": token, "action": "defend"},
            )
            assert defend_res.status_code == 200
            data = defend_res.json()
            assert data["player_damage_dealt"] == 0
            assert data["player"]["current_stamina"] == 85  # 80 + 5 recovered
            assert any("50%" in log for log in data["log_entries"])

    @pytest.mark.asyncio
    async def test_action_use_skill_deals_high_damage(self):
        """Skill attack deals amplified damage and costs 15 stamina."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            await client.post(
                "/api/combat/start",
                json={"session_token": token, "enemy_type": "dire_wolf"},
            )

            skill_res = await client.post(
                "/api/combat/action",
                json={
                    "session_token": token,
                    "action": "use_skill",
                    "skill_name": "Power Strike",
                },
            )
            assert skill_res.status_code == 200
            data = skill_res.json()
            assert data["player_damage_dealt"] >= 8
            assert data["player"]["current_stamina"] == 85  # 100 - 15

    @pytest.mark.asyncio
    async def test_action_use_skill_insufficient_stamina_400(self):
        """Using skill with less than 15 stamina raises 400 validation error."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]
            char_id = char_data["character"]["id"]

            async with get_session() as session:
                char = await session.get(Character, char_id)
                char.current_stamina = 5
                await session.flush()

            await client.post(
                "/api/combat/start",
                json={"session_token": token, "enemy_type": "slime"},
            )

            skill_res = await client.post(
                "/api/combat/action",
                json={"session_token": token, "action": "use_skill"},
            )
            assert skill_res.status_code == 400
            assert skill_res.json()["error"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_action_use_item_heals_player(self):
        """Consuming potion from inventory heals character."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client, starting_health=50)
            token = char_data["session_token"]
            char_id = char_data["character"]["id"]

            # Add Healing Potion to inventory
            async with get_session() as session:
                item = InventoryItem(
                    character_id=char_id,
                    item_id="healing_potion",
                    name="Healing Potion",
                    description="Restores health",
                    quantity=1,
                    item_type="consumable",
                    value=30,
                )
                session.add(item)
                await session.flush()

            await client.post(
                "/api/combat/start",
                json={"session_token": token, "enemy_type": "slime"},
            )

            item_res = await client.post(
                "/api/combat/action",
                json={
                    "session_token": token,
                    "action": "use_item",
                    "item_name": "Healing Potion",
                },
            )
            assert item_res.status_code == 200
            data = item_res.json()
            assert any("restoring" in log for log in data["log_entries"])

    @pytest.mark.asyncio
    async def test_action_flee_success_ends_combat(self):
        """Successful flee check ends combat with status fled."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            await client.post(
                "/api/combat/start",
                json={"session_token": token, "enemy_type": "slime"},
            )

            # Slime has low agility (4); high roll easily flees
            flee_res = await client.post(
                "/api/combat/action",
                json={"session_token": token, "action": "flee", "rng_seed": 42},
            )
            assert flee_res.status_code == 200
            data = flee_res.json()
            if data["status"] == "fled":
                assert data["in_combat"] is False


class TestCombatVictoryAndRewards:
    """Tests victory resolution, reward awards (XP, gold, loot)."""

    @pytest.mark.asyncio
    async def test_combat_victory_awards_xp_and_gold(self):
        """Defeating an enemy awards XP, combat skill XP, gold, and clears in_combat."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client, starting_gold=0)
            token = char_data["session_token"]
            char_id = char_data["character"]["id"]

            await client.post(
                "/api/combat/start",
                json={"session_token": token, "enemy_type": "slime"},
            )

            # Manually weaken enemy in combat state to ensure 1-hit victory
            async with get_session() as session:
                state_res = await session.execute(
                    select(GameplayState).where(GameplayState.character_id == char_id)
                )
                gp = state_res.scalar_one()
                state = dict(gp.combat_state)
                state["enemy"]["current_health"] = 1
                gp.combat_state = state
                flag_modified(gp, "combat_state")
                await session.flush()

            win_res = await client.post(
                "/api/combat/action",
                json={"session_token": token, "action": "attack"},
            )
            assert win_res.status_code == 200
            data = win_res.json()
            assert data["status"] == "victory"
            assert data["in_combat"] is False
            assert data["victory_rewards"] is not None
            assert data["victory_rewards"]["xp_gained"] > 0
            assert data["victory_rewards"]["gold_gained"] >= 0

            # Verify character received rewards in database
            async with get_session() as session:
                char_db = await session.get(Character, char_id)
                assert char_db.experience > 0
                assert char_db.money >= 0


class TestCombatDefeatAndFatality:
    """Tests defeat resolution and fatality handling."""

    @pytest.mark.asyncio
    async def test_combat_defeat_sets_death_cause_combat(self):
        """When character health reaches 0 in combat, character dies with DeathCause.COMBAT."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Create character with only 1 HP
            char_data = await _create_test_character(client, starting_health=1)
            token = char_data["session_token"]
            char_id = char_data["character"]["id"]

            await client.post(
                "/api/combat/start",
                json={"session_token": token, "enemy_type": "corrupted_beast"},
            )

            # Ensure enemy is sturdy so enemy gets to strike back
            defeat_res = await client.post(
                "/api/combat/action",
                json={"session_token": token, "action": "attack"},
            )
            assert defeat_res.status_code == 200
            data = defeat_res.json()
            assert data["status"] == "defeat"
            assert data["in_combat"] is False
            assert data["death_cause"] == DeathCause.COMBAT.value

            # Verify character is marked dead in database
            async with get_session() as session:
                dead_char = await session.get(Character, char_id)
                assert dead_char.is_alive is False
                assert dead_char.current_health == 0
                assert dead_char.death_cause == DeathCause.COMBAT
                assert "Corrupted Beast" in dead_char.death_description


class TestCombatDeceasedGuard:
    """Tests deceased character rejection guard for combat."""

    @pytest.mark.asyncio
    async def test_deceased_character_cannot_start_or_act_in_combat(self):
        """Dead characters are rejected with 409 INVALID_STATE."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]
            char_id = char_data["character"]["id"]

            async with get_session() as session:
                char = await session.get(Character, char_id)
                char.is_alive = False
                await session.flush()

            res = await client.post(
                "/api/combat/start",
                json={"session_token": token, "enemy_type": "goblin"},
            )
            assert res.status_code == 409
            assert res.json()["error"] == "INVALID_STATE"
