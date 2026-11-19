"""Comprehensive test suite for Stage 10 Increment 4: Death and Legacy System.

Verifies:
1. Authoritative death recording (record_death): sets death state, cause, age_at_death, and description.
2. Soul record creation (LifeRecord): captures final attributes, skills, money, inventory, relationships, decisions, and achievements.
3. Legacy generation (CharacterLegacy): strictly respects AGENTS.md §14 (max 1 legacy trait per life), deterministic via session seed.
4. Idempotency: multiple death records for the same character safely return existing records without duplication.
5. REST API endpoints:
   - POST /api/reincarnation/death
   - GET /api/reincarnation/life-record/{character_id}
   - GET /api/reincarnation/legacy/{character_id}
   - GET /api/reincarnation/records?session_token=...
6. Combat defeat triggers automatic death recording (LifeRecord & Legacy created).
7. Event fatality triggers automatic death recording (LifeRecord & Legacy created).
8. Validation and error handling: nonexistent characters, invalid session tokens.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import get_session, recreate_db
from app.core.exceptions import NotFoundError
from app.main import app, lifespan
from app.models.enums import (
    BackgroundName,
    DeathCause,
    EnemyType,
    GenderPresentation,
    LegacyType,
    RaceName,
)
from app.models.gameplay import (
    Character,
    GameSession,
    LifeRecord,
)
from app.services.reincarnation.death import (
    compute_achievements,
    generate_character_legacy,
    record_death,
)


@pytest_asyncio.fixture(autouse=True)
async def isolated_test_db():
    """Ensure database tables are recreated and world is seeded before each test."""
    await recreate_db()
    async with lifespan(app):
        yield


async def _create_test_character(
    client: AsyncClient, name: str = "Test Hero", starting_gold: int = 50
) -> dict:
    """Helper to create a fresh character via API."""
    create_res = await client.post(
        "/api/character/create",
        json={
            "name": name,
            "race_name": RaceName.HUMAN.value,
            "background_name": BackgroundName.COMMONER.value,
            "gender_presentation": GenderPresentation.MALE.value,
        },
    )
    assert create_res.status_code == 201
    char_data = create_res.json()
    char_id = char_data["character"]["id"]

    if starting_gold != 50:
        async with get_session() as session:
            char = await session.get(Character, char_id)
            assert char is not None
            char.money = starting_gold
            await session.commit()

    return char_data


@pytest.mark.asyncio
async def test_record_death_direct_service():
    """Verify authoritative death recording and snapshot creation via direct service call."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        char_data = await _create_test_character(
            client, name="Garrick of Eldoria", starting_gold=120
        )

    char_id = char_data["character"]["id"]

    async with get_session() as session:
        char, life_record, legacy = await record_death(
            session=session,
            character_id=char_id,
            cause=DeathCause.ILLNESS,
            death_description="Succumbed to swamp fever in the southern marshes.",
        )
        await session.commit()

        # Character assertions
        assert char.is_alive is False
        assert char.died_at is not None
        assert char.death_cause == DeathCause.ILLNESS
        assert (
            char.death_description
            == "Succumbed to swamp fever in the southern marshes."
        )
        assert char.age_at_death == 18

        # Life record assertions
        assert life_record.character_id == char_id
        assert life_record.name == "Garrick of Eldoria"
        assert life_record.race_name == RaceName.HUMAN
        assert life_record.background_name == BackgroundName.COMMONER
        assert life_record.cause_of_death == DeathCause.ILLNESS
        assert life_record.days_lived >= 1
        assert life_record.final_money == 120
        assert isinstance(life_record.final_attributes, dict)
        assert "vitality" in life_record.final_attributes
        assert isinstance(life_record.final_skills, dict)
        assert "survival" in life_record.final_skills
        assert isinstance(life_record.final_inventory, list)
        assert isinstance(life_record.achievements, list)
        assert "Eldorian Citizen" in life_record.achievements
        assert "Prosperous Citizen" in life_record.achievements  # since money >= 100

        # Legacy assertions: Max 1 legacy trait per life (AGENTS.md §14)
        assert legacy.character_id == char_id
        assert isinstance(legacy.legacy_type, LegacyType)
        assert legacy.description is not None
        # Either attribute bonus or skill affinity or flavor bonus
        total_bonuses = (1 if legacy.attribute_bonus_value > 0 else 0) + (
            1 if legacy.skill_affinity_bonus > 0 else 0
        )
        assert total_bonuses <= 1

        # Session assertions
        sess_res = await session.execute(
            select(GameSession).where(GameSession.id == char.session_id)
        )
        game_session = sess_res.scalar_one()
        assert game_session.total_deaths == 1
        assert game_session.total_time_lived >= 1


@pytest.mark.asyncio
async def test_record_death_idempotency():
    """Verify that recording death multiple times safely returns existing records."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        char_data = await _create_test_character(client, name="Idempotent Warrior")

    char_id = char_data["character"]["id"]

    async with get_session() as session:
        _, record1, legacy1 = await record_death(
            session=session,
            character_id=char_id,
            cause=DeathCause.SEVERE_INJURIES,
            death_description="First call description",
        )
        await session.commit()

    async with get_session() as session:
        _, record2, legacy2 = await record_death(
            session=session,
            character_id=char_id,
            cause=DeathCause.OLD_AGE,
            death_description="Second call description",
        )
        await session.commit()

        # Must return existing record and legacy without duplicating or mutating original cause
        assert record1.id == record2.id
        assert legacy1.id == legacy2.id
        assert record2.cause_of_death == DeathCause.SEVERE_INJURIES

        # Verify only 1 LifeRecord in DB for this character
        all_records = await session.execute(
            select(LifeRecord).where(LifeRecord.character_id == char_id)
        )
        assert len(all_records.scalars().all()) == 1


@pytest.mark.asyncio
async def test_record_death_nonexistent_character():
    """Verify NotFoundError raised when recording death for an unknown character ID."""
    async with get_session() as session:
        with pytest.raises(NotFoundError):
            await record_death(
                session=session,
                character_id=999999,
                cause=DeathCause.COMBAT,
            )


@pytest.mark.asyncio
async def test_death_endpoint_api():
    """Verify POST /api/reincarnation/death produces full death summary."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        char_data = await _create_test_character(client, name="API Mortal")
        char_id = char_data["character"]["id"]

        death_res = await client.post(
            "/api/reincarnation/death",
            json={
                "character_id": char_id,
                "cause": "dangerous_exploration",
                "death_description": "Plunged into the abyss of the Whispering Mines.",
            },
        )
        assert death_res.status_code == 200
        data = death_res.json()

        assert "perished" in data["message"].lower()
        assert data["character_id"] == char_id
        assert data["is_alive"] is False

        # Check life_record payload
        lr = data["life_record"]
        assert lr["character_id"] == char_id
        assert lr["name"] == "API Mortal"
        assert lr["cause_of_death"] == "dangerous_exploration"
        assert (
            lr["death_description"] == "Plunged into the abyss of the Whispering Mines."
        )
        assert lr["final_money"] == 50

        # Check legacy payload
        leg = data["legacy"]
        assert leg["character_id"] == char_id
        assert "legacy_type" in leg
        assert leg["description"] is not None


@pytest.mark.asyncio
async def test_get_life_record_api():
    """Verify GET /api/reincarnation/life-record/{character_id} retrieves recorded soul record."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        char_data = await _create_test_character(client, name="Record Seeker")
        char_id = char_data["character"]["id"]

        # Before death, 404
        not_found_res = await client.get(f"/api/reincarnation/life-record/{char_id}")
        assert not_found_res.status_code == 404

        # Record death
        await client.post(
            "/api/reincarnation/death",
            json={"character_id": char_id, "cause": "illness"},
        )

        # After death, 200
        get_res = await client.get(f"/api/reincarnation/life-record/{char_id}")
        assert get_res.status_code == 200
        body = get_res.json()
        assert body["character_id"] == char_id
        assert body["name"] == "Record Seeker"
        assert body["cause_of_death"] == "illness"


@pytest.mark.asyncio
async def test_get_character_legacy_api():
    """Verify GET /api/reincarnation/legacy/{character_id} retrieves generated legacy."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        char_data = await _create_test_character(client, name="Legacy Bearer")
        char_id = char_data["character"]["id"]

        # Before death, 404
        not_found_res = await client.get(f"/api/reincarnation/legacy/{char_id}")
        assert not_found_res.status_code == 404

        # Record death
        await client.post(
            "/api/reincarnation/death",
            json={"character_id": char_id, "cause": "combat"},
        )

        # After death, 200
        get_res = await client.get(f"/api/reincarnation/legacy/{char_id}")
        assert get_res.status_code == 200
        body = get_res.json()
        assert body["character_id"] == char_id
        assert "legacy_type" in body
        assert body["description"] is not None


@pytest.mark.asyncio
async def test_get_session_life_records_api():
    """Verify GET /api/reincarnation/records?session_token=... returns session soul records."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        char_data = await _create_test_character(client, name="Session Hero")
        char_id = char_data["character"]["id"]
        session_token = char_data["session_token"]

        # Record death
        await client.post(
            "/api/reincarnation/death",
            json={"character_id": char_id, "cause": "old_age"},
        )

        # Query session records
        rec_res = await client.get(
            f"/api/reincarnation/records?session_token={session_token}"
        )
        assert rec_res.status_code == 200
        body = rec_res.json()
        assert body["session_token"] == session_token
        assert body["total_records"] == 1
        assert body["records"][0]["character_id"] == char_id

        # Query invalid session token -> 404
        invalid_res = await client.get(
            "/api/reincarnation/records?session_token=nonexistent_token"
        )
        assert invalid_res.status_code == 404


@pytest.mark.asyncio
async def test_combat_defeat_triggers_record_death():
    """Verify that falling in combat automatically triggers record_death creating LifeRecord and Legacy."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        char_data = await _create_test_character(client, name="Fallen Soldier")
        char_id = char_data["character"]["id"]
        session_token = char_data["session_token"]

        # Reduce character HP to 1
        async with get_session() as session:
            char = await session.get(Character, char_id)
            assert char is not None
            char.current_health = 1
            await session.commit()

        # Start combat with Goblin
        start_res = await client.post(
            "/api/combat/start",
            json={"session_token": session_token, "enemy_type": EnemyType.GOBLIN.value},
        )
        assert start_res.status_code == 200

        # Player defends; Goblin strikes for >= 1 damage -> defeat
        action_res = await client.post(
            "/api/combat/action",
            json={"session_token": session_token, "action": "defend"},
        )
        assert action_res.status_code == 200
        body = action_res.json()
        assert body["status"] == "defeat"
        assert body["in_combat"] is False
        assert body["player"]["current_health"] == 0
        assert body["death_cause"] == "combat"

        # Verify LifeRecord was automatically created by combat system
        lr_res = await client.get(f"/api/reincarnation/life-record/{char_id}")
        assert lr_res.status_code == 200
        lr_data = lr_res.json()
        assert lr_data["cause_of_death"] == "combat"
        assert "Goblin" in lr_data["death_description"]

        # Verify CharacterLegacy was automatically created
        leg_res = await client.get(f"/api/reincarnation/legacy/{char_id}")
        assert leg_res.status_code == 200


@pytest.mark.asyncio
async def test_event_fatality_triggers_record_death():
    """Verify that dying from event consequences automatically creates LifeRecord and Legacy."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        char_data = await _create_test_character(client, name="Doomed Explorer")
        char_id = char_data["character"]["id"]
        session_token = char_data["session_token"]

        # Reduce character HP to 1
        async with get_session() as session:
            char = await session.get(Character, char_id)
            assert char is not None
            char.current_health = 1
            await session.commit()

        # Trigger highway_brigands event
        trig_res = await client.post(
            "/api/events/trigger",
            json={"session_token": session_token, "event_id": "highway_brigands"},
        )
        assert trig_res.status_code == 200

        # Choose stand_and_fight (damages health by at least -12 -> death)
        choice_res = await client.post(
            "/api/events/choose",
            json={"session_token": session_token, "choice_id": "stand_and_fight"},
        )
        assert choice_res.status_code == 200
        body = choice_res.json()

        # Character health was 1, stand_and_fight inflicts severe damage -> character dead!
        assert body["character_dead"] is True
        assert body["death_cause"] == "event_consequences"

        # Verify LifeRecord was automatically created
        lr_res = await client.get(f"/api/reincarnation/life-record/{char_id}")
        assert lr_res.status_code == 200
        lr_data = lr_res.json()
        assert lr_data["cause_of_death"] == "event_consequences"

        # Verify CharacterLegacy was automatically created
        leg_res = await client.get(f"/api/reincarnation/legacy/{char_id}")
        assert leg_res.status_code == 200
        leg_res = await client.get(f"/api/reincarnation/legacy/{char_id}")
        assert leg_res.status_code == 200


@pytest.mark.asyncio
async def test_legacy_determinism_and_single_trait_constraint():
    """Verify generate_character_legacy generates deterministic single-trait legacies."""
    char = Character(
        id=42,
        name="Test Sage",
        generation=1,
        death_cause=DeathCause.OLD_AGE,
    )
    final_attrs = {
        "strength": 12,
        "vitality": 16,
        "intelligence": 15,
        "agility": 10,
        "luck": 8,
    }
    final_skills = {"swordsmanship": 2, "magic": 4, "survival": 3}

    legacy1 = generate_character_legacy(
        character=char,
        session_seed=12345,
        generation=1,
        final_attributes=final_attrs,
        final_skills=final_skills,
    )

    legacy2 = generate_character_legacy(
        character=char,
        session_seed=12345,
        generation=1,
        final_attributes=final_attrs,
        final_skills=final_skills,
    )

    # Determinism
    assert legacy1.legacy_type == legacy2.legacy_type
    assert legacy1.attribute_bonus == legacy2.attribute_bonus
    assert legacy1.attribute_bonus_value == legacy2.attribute_bonus_value
    assert legacy1.skill_affinity == legacy2.skill_affinity
    assert legacy1.skill_affinity_bonus == legacy2.skill_affinity_bonus

    # Single trait constraint: never grant both an attribute bonus and a skill affinity bonus
    has_attr = legacy1.attribute_bonus_value > 0
    has_skill = legacy1.skill_affinity_bonus > 0
    assert not (has_attr and has_skill), "Legacy violated single trait constraint!"


@pytest.mark.asyncio
async def test_achievements_computation():
    """Verify compute_achievements awards expected titles based on milestones."""
    char = Character(
        id=1,
        name="Legendary Hero",
        money=350,
        level=4,
        reputation=25,
    )
    skills = {"swordsmanship": 5, "magic": 3}
    relationships = {"1": 40, "2": -35}

    achievements = compute_achievements(
        character=char,
        days_lived=35,
        final_skills=skills,
        final_relationships=relationships,
    )

    assert "Eldorian Citizen" in achievements
    assert "Survivor of the First Week" in achievements
    assert "Seasoned Wanderer" in achievements
    assert "Wealthy Merchant" in achievements
    assert "Ascendant Adventurer" in achievements
    assert "Blade Apprentice" in achievements
    assert "Swordmaster" in achievements
    assert "Acolyte of Arcana" in achievements
    assert "Celebrated Hero" in achievements
    assert "Beloved Companion" in achievements
    assert "Bitter Rival" in achievements
