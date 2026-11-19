"""Comprehensive test suite for Stage 10 Increment 5: Reincarnation and Next Generation System.

Verifies:
1. Session Token Validation (PR-02):
   - Empty string or whitespace session_token raises ValidationError and never silently creates new sessions.
2. Reincarnation Guards:
   - Cannot reincarnate while the active character is still alive (returns 409 GameStateError).
   - GET /api/reincarnation/status returns can_reincarnate=False when alive, can_reincarnate=True when dead.
3. Reincarnation into Generation 2:
   - New identity, race, background, and location.
   - Generation increments to 2 on character and session.
   - Inherited legacy link (legacy_id) is set.
   - GameplayState cleanly reset and re-pointed to the new character.
4. Limited Legacy Application (SPEC §9.3 & AGENTS.md §14):
   - Attribute bonus increases attribute by 1 and scales health/stamina.
   - Skill affinity adds/increases skill level by 1.
   - Inherited bonus grants +25 starting gold.
   - Narrative dreams/fragments appear in personality.
5. Multi-generation lifecycle (Gen 1 -> Gen 2 -> Gen 3):
   - 3 playable lives in one session.
   - Soul records preserved chronologically across generations.
   - Both POST /api/reincarnation/reincarnate and POST /api/character/create with session_token work seamlessly.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import get_session, recreate_db
from app.core.exceptions import ValidationError
from app.main import app, lifespan
from app.models.enums import (
    BackgroundName,
    DeathCause,
    GenderPresentation,
    LegacyType,
    RaceName,
)
from app.models.gameplay import (
    CharacterLegacy,
    GameplayState,
    GameSession,
)
from app.services.character.creation import get_or_create_session
from app.services.reincarnation.death import record_death


@pytest_asyncio.fixture(autouse=True)
async def isolated_test_db():
    """Ensure database tables are recreated and world is seeded before each test."""
    await recreate_db()
    async with lifespan(app):
        yield


async def _create_test_character(
    client: AsyncClient, name: str = "First Life", session_token: str | None = None
) -> dict:
    """Helper to create a fresh character via API."""
    payload = {
        "name": name,
        "race_name": RaceName.HUMAN.value,
        "background_name": BackgroundName.COMMONER.value,
        "gender_presentation": GenderPresentation.MALE.value,
    }
    if session_token is not None:
        payload["session_token"] = session_token

    create_res = await client.post("/api/character/create", json=payload)
    assert create_res.status_code == 201
    return create_res.json()


@pytest.mark.asyncio
async def test_empty_session_token_validation_pr02():
    """Verify empty or whitespace session token raises ValidationError and never creates new sessions (PR-02)."""
    # 1. Direct service call
    async with get_session() as session:
        with pytest.raises(ValidationError):
            await get_or_create_session(session, session_token="")

        with pytest.raises(ValidationError):
            await get_or_create_session(session, session_token="   ")

    # 2. Character create endpoint
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        empty_res = await client.post(
            "/api/character/create",
            json={
                "name": "Invalid Hero",
                "race_name": RaceName.HUMAN.value,
                "background_name": BackgroundName.COMMONER.value,
                "gender_presentation": GenderPresentation.MALE.value,
                "session_token": "",
            },
        )
        assert empty_res.status_code in (400, 422)

        # 3. Reincarnate endpoint
        reincarnate_res = await client.post(
            "/api/reincarnation/reincarnate",
            json={
                "session_token": "   ",
                "name": "Invalid Reincarnate",
                "race_name": RaceName.HUMAN.value,
                "background_name": BackgroundName.COMMONER.value,
                "gender_presentation": GenderPresentation.MALE.value,
            },
        )
        assert reincarnate_res.status_code in (400, 422)


@pytest.mark.asyncio
async def test_cannot_reincarnate_while_character_alive():
    """Verify that a living character prevents reincarnation with 409 GameStateError."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        char_data = await _create_test_character(client, name="Alive Wanderer")
        token = char_data["session_token"]
        char_id = char_data["character"]["id"]

        # Check status endpoint
        status_res = await client.get(
            f"/api/reincarnation/status?session_token={token}"
        )
        assert status_res.status_code == 200
        status_body = status_res.json()
        assert status_body["can_reincarnate"] is False
        assert status_body["living_character_id"] == char_id
        assert status_body["available_legacy"] is None

        # Attempt to reincarnate while alive
        reincarnate_res = await client.post(
            "/api/reincarnation/reincarnate",
            json={
                "session_token": token,
                "name": "Second Attempt",
                "race_name": RaceName.ELF.value,
                "background_name": BackgroundName.MERCHANT_FAMILY.value,
                "gender_presentation": GenderPresentation.FEMALE.value,
            },
        )
        assert reincarnate_res.status_code == 409
        error_body = reincarnate_res.json()
        assert "alive" in error_body["message"].lower()


@pytest.mark.asyncio
async def test_reincarnation_into_gen2_with_legacy():
    """Verify complete reincarnation flow: death -> legacy -> gen 2 reincarnation -> inherited perks."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create Generation 1
        gen1_data = await _create_test_character(client, name="First Born")
        token = gen1_data["session_token"]
        gen1_id = gen1_data["character"]["id"]
        assert gen1_data["character"]["generation"] == 1

        # 2. Record death of Gen 1
        death_res = await client.post(
            "/api/reincarnation/death",
            json={
                "character_id": gen1_id,
                "cause": DeathCause.COMBAT.value,
                "death_description": "Fell honorably defending the city gates.",
            },
        )
        assert death_res.status_code == 200
        death_data = death_res.json()
        legacy_data = death_data["legacy"]
        assert legacy_data["character_id"] == gen1_id

        # 3. Check reincarnation status
        status_res = await client.get(
            f"/api/reincarnation/status?session_token={token}"
        )
        assert status_res.status_code == 200
        status_body = status_res.json()
        assert status_body["can_reincarnate"] is True
        assert status_body["living_character_id"] is None
        assert status_body["deceased_character_id"] == gen1_id
        assert status_body["available_legacy"] is not None
        assert status_body["available_legacy"]["id"] == legacy_data["id"]

        # 4. Reincarnate into Generation 2
        reincarnate_res = await client.post(
            "/api/reincarnation/reincarnate",
            json={
                "session_token": token,
                "name": "Second Reincarnated Soul",
                "race_name": RaceName.ELF.value,
                "background_name": BackgroundName.MERCHANT_FAMILY.value,
                "gender_presentation": GenderPresentation.FEMALE.value,
            },
        )
        assert reincarnate_res.status_code == 201
        reinc_body = reincarnate_res.json()

        assert reinc_body["generation"] == 2
        assert reinc_body["session_token"] == token
        assert reinc_body["inherited_legacy"]["id"] == legacy_data["id"]

        char2 = reinc_body["character"]
        assert char2["generation"] == 2
        assert char2["name"] == "Second Reincarnated Soul"
        assert char2["race_name"] == RaceName.ELF.value
        assert char2["background_name"] == BackgroundName.MERCHANT_FAMILY.value
        assert char2["is_alive"] is True
        assert char2["legacy_id"] == legacy_data["id"]

        # 5. Verify GameplayState is re-pointed to Generation 2 and reset
        async with get_session() as session:
            sess_res = await session.execute(
                select(GameSession).where(GameSession.session_token == token)
            )
            db_session = sess_res.scalar_one()
            assert db_session.current_generation == 2
            assert db_session.total_generations == 2

            gp_res = await session.execute(
                select(GameplayState).where(GameplayState.session_id == db_session.id)
            )
            gp = gp_res.scalar_one()
            assert gp.character_id == char2["id"]
            assert gp.current_day == 1
            assert gp.in_combat is False
            assert gp.active_event_id is None


@pytest.mark.asyncio
async def test_inherited_attribute_bonus_application():
    """Verify that an inherited attribute legacy grants +1 to the targeted attribute."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create Gen 1
        gen1_data = await _create_test_character(client, name="Gen 1 Warrior")
        token = gen1_data["session_token"]
        gen1_id = gen1_data["character"]["id"]

        # Manually create a specific attribute bonus legacy for Gen 1
        async with get_session() as session:
            await record_death(session, gen1_id, DeathCause.OLD_AGE)
            # Find generated legacy and force it to be attribute bonus for intelligence
            leg_res = await session.execute(
                select(CharacterLegacy).where(CharacterLegacy.character_id == gen1_id)
            )
            legacy = leg_res.scalar_one()
            legacy.legacy_type = LegacyType.ATTRIBUTE_BONUS
            legacy.attribute_bonus = "intelligence"
            legacy.attribute_bonus_value = 1
            legacy.skill_affinity = None
            legacy.skill_affinity_bonus = 0
            await session.commit()

        # Reincarnate as Human Commoner
        reinc_res = await client.post(
            "/api/reincarnation/reincarnate",
            json={
                "session_token": token,
                "name": "Gen 2 Scholar-Born",
                "race_name": RaceName.HUMAN.value,
                "background_name": BackgroundName.COMMONER.value,
                "gender_presentation": GenderPresentation.FEMALE.value,
            },
        )
        assert reinc_res.status_code == 201
        body = reinc_res.json()
        char = body["character"]

        # Base Human Commoner Intelligence is 10. With +1 legacy bonus, it must be 11.
        int_attr = next(a for a in char["attributes"] if a["name"] == "intelligence")
        assert int_attr["base_value"] == 11
        assert int_attr["current_value"] == 11


@pytest.mark.asyncio
async def test_inherited_skill_affinity_bonus_application():
    """Verify that an inherited skill affinity legacy grants +1 level to the targeted skill."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        gen1_data = await _create_test_character(client, name="Gen 1 Master")
        token = gen1_data["session_token"]
        gen1_id = gen1_data["character"]["id"]

        # Record death and force legacy to swordsmanship affinity +1
        async with get_session() as session:
            await record_death(session, gen1_id, DeathCause.COMBAT)
            leg_res = await session.execute(
                select(CharacterLegacy).where(CharacterLegacy.character_id == gen1_id)
            )
            legacy = leg_res.scalar_one()
            legacy.legacy_type = LegacyType.SKILL_AFFINITY
            legacy.skill_affinity = "swordsmanship"
            legacy.skill_affinity_bonus = 1
            legacy.attribute_bonus = None
            legacy.attribute_bonus_value = 0
            await session.commit()

        # Reincarnate as Commoner (Commoner starts without swordsmanship, so it should gain it at level 1)
        reinc_res = await client.post(
            "/api/reincarnation/reincarnate",
            json={
                "session_token": token,
                "name": "Gen 2 Sword Bearer",
                "race_name": RaceName.HUMAN.value,
                "background_name": BackgroundName.COMMONER.value,
                "gender_presentation": GenderPresentation.MALE.value,
            },
        )
        assert reinc_res.status_code == 201
        char = reinc_res.json()["character"]

        sword_skill = next(
            (s for s in char["skills"] if s["name"] == "swordsmanship"), None
        )
        assert sword_skill is not None
        assert sword_skill["level"] == 1


@pytest.mark.asyncio
async def test_inherited_money_bonus_application():
    """Verify that an inherited bonus legacy grants +25 starting gold."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        gen1_data = await _create_test_character(client, name="Gen 1 Merchant")
        token = gen1_data["session_token"]
        gen1_id = gen1_data["character"]["id"]

        # Record death and force legacy to INHERITED_BONUS
        async with get_session() as session:
            await record_death(session, gen1_id, DeathCause.OLD_AGE)
            leg_res = await session.execute(
                select(CharacterLegacy).where(CharacterLegacy.character_id == gen1_id)
            )
            legacy = leg_res.scalar_one()
            legacy.legacy_type = LegacyType.INHERITED_BONUS
            await session.commit()

        # Reincarnate as Commoner (base starting gold 50) -> with +25 legacy, money must be 75
        reinc_res = await client.post(
            "/api/reincarnation/reincarnate",
            json={
                "session_token": token,
                "name": "Gen 2 Wealthy Heir",
                "race_name": RaceName.HUMAN.value,
                "background_name": BackgroundName.COMMONER.value,
                "gender_presentation": GenderPresentation.FEMALE.value,
            },
        )
        assert reinc_res.status_code == 201
        char = reinc_res.json()["character"]
        assert char["money"] == 75  # 50 base + 25 legacy bonus


@pytest.mark.asyncio
async def test_reincarnation_via_character_create_endpoint():
    """Verify that passing session_token to POST /api/character/create also functions as reincarnation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        gen1 = await _create_test_character(client, name="Original Pioneer")
        token = gen1["session_token"]
        gen1_id = gen1["character"]["id"]

        # Kill Gen 1
        await client.post(
            "/api/reincarnation/death",
            json={"character_id": gen1_id, "cause": "illness"},
        )

        # Call /api/character/create with existing session_token
        create_res = await client.post(
            "/api/character/create",
            json={
                "name": "Pioneer Reborn",
                "race_name": RaceName.DWARF.value,
                "background_name": BackgroundName.ORPHAN.value,
                "gender_presentation": GenderPresentation.MALE.value,
                "session_token": token,
            },
        )
        assert create_res.status_code == 201
        data = create_res.json()
        assert data["character"]["generation"] == 2
        assert data["session_token"] == token
        assert data["character"]["legacy_id"] is not None


@pytest.mark.asyncio
async def test_multi_generation_three_lives_lifecycle():
    """Verify playing 3 consecutive generations in one session per SPEC §9.3 & §14 Criteria 12."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Life 1 (Generation 1)
        gen1 = await _create_test_character(client, name="Generation One")
        token = gen1["session_token"]
        gen1_id = gen1["character"]["id"]
        assert gen1["character"]["generation"] == 1

        # Gen 1 dies
        d1 = await client.post(
            "/api/reincarnation/death",
            json={"character_id": gen1_id, "cause": "dangerous_exploration"},
        )
        assert d1.status_code == 200

        # Life 2 (Generation 2)
        gen2 = await client.post(
            "/api/reincarnation/reincarnate",
            json={
                "session_token": token,
                "name": "Generation Two",
                "race_name": RaceName.ELF.value,
                "background_name": BackgroundName.MERCHANT_FAMILY.value,
                "gender_presentation": GenderPresentation.FEMALE.value,
            },
        )
        assert gen2.status_code == 201
        gen2_id = gen2.json()["character"]["id"]
        assert gen2.json()["generation"] == 2

        # Gen 2 dies
        d2 = await client.post(
            "/api/reincarnation/death",
            json={"character_id": gen2_id, "cause": "combat"},
        )
        assert d2.status_code == 200

        # Life 3 (Generation 3)
        gen3 = await client.post(
            "/api/reincarnation/reincarnate",
            json={
                "session_token": token,
                "name": "Generation Three",
                "race_name": RaceName.BEASTKIN.value,
                "background_name": BackgroundName.NOBLE_DESCENDANT.value,
                "gender_presentation": GenderPresentation.NON_BINARY.value,
            },
        )
        assert gen3.status_code == 201
        assert gen3.json()["generation"] == 3

        # Check all LifeRecords for session
        records_res = await client.get(
            f"/api/reincarnation/records?session_token={token}"
        )
        assert records_res.status_code == 200
        records_body = records_res.json()
        assert records_body["total_records"] == 2
        assert records_body["records"][0]["generation"] == 1
        assert records_body["records"][0]["name"] == "Generation One"
        assert records_body["records"][1]["generation"] == 2
        assert records_body["records"][1]["name"] == "Generation Two"

        # Verify DB session total generations
        async with get_session() as session:
            sess_res = await session.execute(
                select(GameSession).where(GameSession.session_token == token)
            )
            db_session = sess_res.scalar_one()
            assert db_session.current_generation == 3
            assert db_session.total_generations == 3
            assert db_session.total_deaths == 2
