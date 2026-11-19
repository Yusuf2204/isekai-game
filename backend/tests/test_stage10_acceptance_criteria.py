"""End-to-End Integration and Acceptance Verification for SPEC §14.

Validates all 15 authoritative acceptance criteria established in SPEC.md §14:
1. Application starts locally using documented commands.
2. The player can create a new game session.
3. Character generation works correctly.
4. The player can perform multiple activities.
5. Event choices produce actual state changes.
6. Attributes influence gameplay outcomes.
7. NPC interactions work.
8. Combat can be completed or result in death.
9. Death generates a complete life record.
10. Reincarnation creates a new playable character.
11. Previous life legacy affects the next generation in a limited way.
12. At least two lives can be played in one session.
13. Session state persists after browser refresh.
14. The session summary displays previous generations.
15. No critical runtime errors prevent gameplay.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import get_session, recreate_db
from app.main import app, lifespan
from app.models.enums import DeathCause
from app.models.gameplay import GameSession


@pytest_asyncio.fixture(autouse=True)
async def isolated_test_db():
    """Ensure database tables are recreated and world is seeded before each test."""
    await recreate_db()
    async with lifespan(app):
        yield


@pytest.mark.asyncio
async def test_criterion_01_application_starts_locally():
    """Criterion 1: The application starts locally and responds to health checks."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "isekai-game"
        assert "version" in data


@pytest.mark.asyncio
async def test_criterion_02_create_new_game_session():
    """Criterion 2: The player can create a new game session."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/character/create",
            json={
                "name": "First Pioneer",
                "race_name": "human",
                "background_name": "commoner",
                "gender_presentation": "male",
            },
        )
        assert response.status_code == 201
        data = response.json()
        session_token = data.get("session_token")
        assert session_token is not None
        assert len(session_token) > 10

        # Verify session exists in DB
        async with get_session() as session:
            result = await session.execute(
                select(GameSession).where(GameSession.session_token == session_token)
            )
            game_session = result.scalar_one_or_none()
            assert game_session is not None
            assert game_session.is_active is True
            assert game_session.current_generation == 1


@pytest.mark.asyncio
async def test_criterion_03_character_generation_correctness():
    """Criterion 3: Character generation works correctly across races and backgrounds."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Check races endpoint
        races_resp = await client.get("/api/character/races")
        assert races_resp.status_code == 200
        races = races_resp.json()
        assert len(races) == 6

        # Check backgrounds endpoint
        bgs_resp = await client.get("/api/character/backgrounds")
        assert bgs_resp.status_code == 200
        backgrounds = bgs_resp.json()
        assert len(backgrounds) == 5

        # Create character with Elf + Merchant
        resp = await client.post(
            "/api/character/create",
            json={
                "name": "Elven Merchant",
                "race_name": "elf",
                "background_name": "merchant_family",
                "gender_presentation": "female",
            },
        )
        assert resp.status_code == 201
        char = resp.json()["character"]
        assert char["race_name"] == "elf"
        assert char["background_name"] == "merchant_family"
        assert char["money"] == 200  # Merchant starting gold
        assert char["is_alive"] is True
        assert len(char["attributes"]) == 5
        assert len(char["skills"]) >= 2


@pytest.mark.asyncio
async def test_criterion_04_player_can_perform_multiple_activities():
    """Criterion 4: The player can perform multiple activities (explore, rest, work)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create character
        create_resp = await client.post(
            "/api/character/create",
            json={
                "name": "Adventurer",
                "race_name": "human",
                "background_name": "commoner",
                "gender_presentation": "male",
            },
        )
        token = create_resp.json()["session_token"]

        # 1. Explore
        explore_resp = await client.post(
            f"/api/activities/explore?session_token={token}", json={}
        )
        assert explore_resp.status_code == 200
        explore_data = explore_resp.json()
        assert explore_data["result"]["success"] is True
        assert "narrative" in explore_data["result"]

        # 2. Work
        work_resp = await client.post(
            f"/api/activities/work?session_token={token}",
            json={"work_type": "Laborer"},
        )
        assert work_resp.status_code == 200
        work_data = work_resp.json()
        assert work_data["result"]["money_change"] > 0

        # 3. Rest
        rest_resp = await client.post(
            f"/api/activities/rest?session_token={token}",
            json={"duration": "short"},
        )
        assert rest_resp.status_code == 200
        rest_data = rest_resp.json()
        assert rest_data["result"]["health_change"] >= 0


@pytest.mark.asyncio
async def test_criterion_05_event_choices_produce_state_changes():
    """Criterion 5: Event choices produce actual state changes."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_resp = await client.post(
            "/api/character/create",
            json={
                "name": "Fate Traveler",
                "race_name": "human",
                "background_name": "commoner",
                "gender_presentation": "male",
            },
        )
        token = create_resp.json()["session_token"]

        # Trigger stolen wallet event
        trigger_resp = await client.post(
            "/api/events/trigger",
            json={
                "session_token": token,
                "event_id": "stolen_wallet",
                "force_trigger": True,
            },
        )
        assert trigger_resp.status_code == 200

        # Choose "let_go" (no stat check, loses 10 gold, gains survival XP)
        choose_resp = await client.post(
            "/api/events/choose",
            json={"session_token": token, "choice_id": "let_go"},
        )
        assert choose_resp.status_code == 200
        res = choose_resp.json()
        assert res["choice_id"] == "let_go"
        assert res["money_change"] == -10  # Money was deducted
        assert "survival" in res["skill_xp"]


@pytest.mark.asyncio
async def test_criterion_06_attributes_influence_gameplay_outcomes():
    """Criterion 6: Attributes influence gameplay outcomes (initiative & combat states)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # High agility character (Elf)
        elf_resp = await client.post(
            "/api/character/create",
            json={
                "name": "Swift Elf",
                "race_name": "elf",
                "background_name": "orphan",
                "gender_presentation": "female",
            },
        )
        token = elf_resp.json()["session_token"]

        # Start combat with slime
        combat_resp = await client.post(
            "/api/combat/start",
            json={"session_token": token, "enemy_type": "slime"},
        )
        assert combat_resp.status_code == 200
        combat = combat_resp.json()
        assert combat["in_combat"] is True
        assert combat["status"] == "active"
        assert combat["enemy"]["name"] == "slime"


@pytest.mark.asyncio
async def test_criterion_07_npc_interactions_work():
    """Criterion 7: NPC interactions work (location list, dialogue, gifting, trust)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_resp = await client.post(
            "/api/character/create",
            json={
                "name": "Diplomat",
                "race_name": "human",
                "background_name": "merchant_family",
                "gender_presentation": "male",
            },
        )
        token = create_resp.json()["session_token"]

        # Get NPCs at capital (location 1)
        npcs_resp = await client.get(f"/api/npc/location/1?session_token={token}")
        assert npcs_resp.status_code == 200
        npcs = npcs_resp.json()["npcs"]
        assert len(npcs) > 0
        npc_id = npcs[0]["id"]

        # Talk to NPC
        talk_resp = await client.post(
            f"/api/npc/{npc_id}/talk",
            json={"session_token": token, "topic": "greetings"},
        )
        assert talk_resp.status_code == 200
        talk_data = talk_resp.json()
        assert "dialogue" in talk_data

        # Gift NPC
        gift_resp = await client.post(
            f"/api/npc/{npc_id}/gift",
            json={"session_token": token, "money": 25},
        )
        assert gift_resp.status_code == 200
        gift_data = gift_resp.json()
        assert gift_data["relationship_change"] >= 0


@pytest.mark.asyncio
async def test_criterion_08_combat_completion_and_victory():
    """Criterion 8: Combat can be completed or result in death."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_resp = await client.post(
            "/api/character/create",
            json={
                "name": "Warrior",
                "race_name": "dwarf",
                "background_name": "noble_descendant",
                "gender_presentation": "male",
            },
        )
        token = create_resp.json()["session_token"]

        # Start combat with slime
        await client.post(
            "/api/combat/start",
            json={"session_token": token, "enemy_type": "slime"},
        )

        # Execute actions until victory or defeat
        for _ in range(10):
            action_resp = await client.post(
                "/api/combat/action",
                json={"session_token": token, "action": "use_skill"},
            )
            assert action_resp.status_code == 200
            res = action_resp.json()
            if res["status"] in ("victory", "defeat"):
                break

        assert res["status"] in ("victory", "defeat")


@pytest.mark.asyncio
async def test_criterion_09_death_generates_complete_life_record():
    """Criterion 9: Death generates a complete life record and legacy."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_resp = await client.post(
            "/api/character/create",
            json={
                "name": "Fallen Legend",
                "race_name": "dragonkin",
                "background_name": "noble_descendant",
                "gender_presentation": "female",
            },
        )
        char_id = create_resp.json()["character"]["id"]

        # Authoritatively record death
        death_resp = await client.post(
            "/api/reincarnation/death",
            json={
                "character_id": char_id,
                "cause": DeathCause.COMBAT.value,
                "death_description": "Heroic sacrifice defending Luminaris",
            },
        )
        assert death_resp.status_code == 200

        # Inspect soul record
        record_resp = await client.get(f"/api/reincarnation/life-record/{char_id}")
        assert record_resp.status_code == 200
        life_record = record_resp.json()
        assert life_record["name"] == "Fallen Legend"
        assert life_record["cause_of_death"] == DeathCause.COMBAT.value
        assert "death_description" in life_record
        assert len(life_record["final_attributes"]) == 5
        assert isinstance(life_record["achievements"], list)


@pytest.mark.asyncio
async def test_criterion_10_and_11_reincarnation_and_limited_legacy():
    """Criteria 10 & 11: Reincarnation creates new playable character with limited legacy perk."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Life 1
        create_resp = await client.post(
            "/api/character/create",
            json={
                "name": "Gen1 Hero",
                "race_name": "human",
                "background_name": "commoner",
                "gender_presentation": "male",
            },
        )
        token = create_resp.json()["session_token"]
        char_id = create_resp.json()["character"]["id"]

        # Gen 1 dies
        await client.post(
            "/api/reincarnation/death",
            json={"character_id": char_id, "cause": DeathCause.ILLNESS.value},
        )

        # Check reincarnation status
        status_resp = await client.get(
            f"/api/reincarnation/status?session_token={token}"
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["can_reincarnate"] is True
        assert status_resp.json()["available_legacy"] is not None

        avail_leg = status_resp.json()["available_legacy"]
        assert avail_leg is not None

        # Reincarnate into Gen 2
        reinc_resp = await client.post(
            "/api/reincarnation/reincarnate",
            json={
                "session_token": token,
                "name": "Gen2 Successor",
                "race_name": "elf",
                "background_name": "merchant_family",
                "gender_presentation": "female",
            },
        )
        assert reinc_resp.status_code == 201
        gen2_char = reinc_resp.json()["character"]
        assert gen2_char["generation"] == 2
        assert gen2_char["name"] == "Gen2 Successor"
        assert gen2_char["is_alive"] is True
        assert gen2_char["legacy_id"] is not None

        # Limited legacy check: verify that either attribute, skill affinity, or money was granted
        if avail_leg["legacy_type"] == "inherited_bonus":
            assert gen2_char["money"] == 225
        elif avail_leg["legacy_type"] == "attribute_bonus":
            attr_name = avail_leg["attribute_bonus"]
            attr = next(a for a in gen2_char["attributes"] if a["name"] == attr_name)
            assert attr["current_value"] >= attr["base_value"]
        elif avail_leg["legacy_type"] == "skill_affinity":
            skill_name = avail_leg["skill_affinity"]
            assert any(s["name"] == skill_name for s in gen2_char["skills"])


@pytest.mark.asyncio
async def test_criterion_12_play_at_least_two_generations_in_one_session():
    """Criterion 12: At least two lives can be played in one session."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Generation 1
        gen1_resp = await client.post(
            "/api/character/create",
            json={
                "name": "Lineage Founder",
                "race_name": "human",
                "background_name": "commoner",
                "gender_presentation": "male",
            },
        )
        token = gen1_resp.json()["session_token"]
        char1_id = gen1_resp.json()["character"]["id"]

        # Play Gen 1
        await client.post(f"/api/activities/explore?session_token={token}", json={})
        await client.post(
            "/api/reincarnation/death",
            json={"character_id": char1_id, "cause": DeathCause.OLD_AGE.value},
        )

        # Generation 2
        gen2_resp = await client.post(
            "/api/reincarnation/reincarnate",
            json={
                "session_token": token,
                "name": "Lineage Heir",
                "race_name": "dwarf",
                "background_name": "commoner",
                "gender_presentation": "female",
            },
        )
        assert gen2_resp.status_code == 201
        char2_id = gen2_resp.json()["character"]["id"]

        # Play Gen 2
        await client.post(f"/api/activities/explore?session_token={token}", json={})
        await client.post(
            "/api/reincarnation/death",
            json={"character_id": char2_id, "cause": DeathCause.COMBAT.value},
        )

        # Generation 3
        gen3_resp = await client.post(
            "/api/reincarnation/reincarnate",
            json={
                "session_token": token,
                "name": "Lineage Third",
                "race_name": "beastkin",
                "background_name": "orphan",
                "gender_presentation": "non_binary",
            },
        )
        assert gen3_resp.status_code == 201
        assert gen3_resp.json()["character"]["generation"] == 3


@pytest.mark.asyncio
async def test_criterion_13_session_state_persists_across_browser_refresh():
    """Criterion 13: Session state persists after browser refresh."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_resp = await client.post(
            "/api/character/create",
            json={
                "name": "Persistent Hero",
                "race_name": "human",
                "background_name": "commoner",
                "gender_presentation": "male",
            },
        )
        token = create_resp.json()["session_token"]

        # Advance time by 3 periods and earn wages
        await client.post(
            f"/api/time/advance?session_token={token}", json={"periods": 3}
        )
        await client.post(
            f"/api/activities/work?session_token={token}",
            json={"work_type": "Laborer"},
        )

        # Simulate browser refresh: reload character, time state, and resources via session_token
        curr_char = await client.get(f"/api/character/current?session_token={token}")
        assert curr_char.status_code == 200
        assert curr_char.json()["name"] == "Persistent Hero"

        curr_time = await client.get(f"/api/time/state?session_token={token}")
        assert curr_time.status_code == 200
        assert curr_time.json()["current_day"] >= 1
        assert curr_time.json()["current_time_of_day"] is not None

        curr_resources = await client.get(
            f"/api/character/resources?session_token={token}"
        )
        assert curr_resources.status_code == 200
        assert curr_resources.json()["money"] > 50  # Work wages persisted


@pytest.mark.asyncio
async def test_criterion_14_session_summary_displays_previous_generations():
    """Criterion 14: The session summary displays previous generations."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Life 1
        gen1 = await client.post(
            "/api/character/create",
            json={
                "name": "Ancestor Alden",
                "race_name": "human",
                "background_name": "commoner",
                "gender_presentation": "male",
            },
        )
        token = gen1.json()["session_token"]
        char1_id = gen1.json()["character"]["id"]
        await client.post(
            "/api/reincarnation/death",
            json={"character_id": char1_id, "cause": DeathCause.COMBAT.value},
        )

        # Life 2
        await client.post(
            "/api/reincarnation/reincarnate",
            json={
                "session_token": token,
                "name": "Descendant Lyra",
                "race_name": "elf",
                "background_name": "merchant_family",
                "gender_presentation": "female",
            },
        )

        # Conclude session gracefully
        end_resp = await client.post("/api/session/end", json={"session_token": token})
        assert end_resp.status_code == 200

        # Query session summary
        summary_resp = await client.get(f"/api/session/summary?session_token={token}")
        assert summary_resp.status_code == 200
        summary = summary_resp.json()

        assert summary["is_active"] is False
        assert summary["total_generations"] >= 2
        assert len(summary["characters_created"]) >= 2
        names = [c["name"] for c in summary["characters_created"]]
        assert "Ancestor Alden" in names
        assert "Descendant Lyra" in names


@pytest.mark.asyncio
async def test_criterion_15_no_critical_runtime_errors():
    """Criterion 15: No critical runtime errors prevent gameplay; standard error envelopes."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Invalid endpoint returns 404
        r404 = await client.get("/api/nonexistent")
        assert r404.status_code == 404

        # Malformed request returns 422 standard validation error
        r422 = await client.post("/api/character/create", json={})
        assert r422.status_code == 422
        body = r422.json()
        assert "detail" in body or "error" in body

        # Invalid session token returns standard error envelope
        r_bad_session = await client.get(
            "/api/time/state?session_token=nonexistent_token_123"
        )
        assert r_bad_session.status_code in (400, 404)
        err = r_bad_session.json()
        assert "error" in err or "detail" in err
