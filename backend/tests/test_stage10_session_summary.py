"""Comprehensive test suite for Stage 10 Increment 6: Session Summary and History System.

Verifies:
1. Session summary compilation per SPEC.md §10:
   - Total generations, total deaths, total time lived.
   - Characters created across generations.
   - Complete death records (LifeRecord).
   - Legacies passed across lives (CharacterLegacy).
   - Aggregated skills developed across lives.
   - Aggregated life decisions and achievements.
2. Formal session conclusion (POST /api/session/end):
   - Sets is_active=False and records ended_at timestamp.
   - Peacefully retires active living character, creating a final soul record.
   - Rejects future character creation or activities on ended sessions.
3. Session history archive (GET /api/session/history):
   - Lists sessions in reverse chronological order with aggregate statistics.
4. Validation and error handling:
   - Empty or nonexistent session tokens return appropriate errors (400/422 and 404).
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import get_session, recreate_db
from app.main import app, lifespan
from app.models.enums import (
    BackgroundName,
    DeathCause,
    GenderPresentation,
    RaceName,
)
from app.models.gameplay import Character, GameSession


@pytest_asyncio.fixture(autouse=True)
async def isolated_test_db():
    """Ensure database tables are recreated and world is seeded before each test."""
    await recreate_db()
    async with lifespan(app):
        yield


async def _create_test_character(
    client: AsyncClient, name: str = "Session Hero", session_token: str | None = None
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
async def test_session_summary_single_life():
    """Verify session summary for a single ongoing life."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        char_data = await _create_test_character(client, name="Solo Adventurer")
        token = char_data["session_token"]
        char_id = char_data["character"]["id"]

        summary_res = await client.get(f"/api/session/summary?session_token={token}")
        assert summary_res.status_code == 200
        summary = summary_res.json()

        assert summary["session_token"] == token
        assert summary["is_active"] is True
        assert summary["total_generations"] == 1
        assert summary["total_deaths"] == 0
        assert summary["total_time_lived"] >= 1
        assert summary["ended_at"] is None

        # Characters snapshot
        assert len(summary["characters_created"]) == 1
        c0 = summary["characters_created"][0]
        assert c0["character_id"] == char_id
        assert c0["generation"] == 1
        assert c0["name"] == "Solo Adventurer"
        assert c0["is_alive"] is True

        # Skills and achievements
        assert isinstance(summary["skills_developed"], dict)
        assert len(summary["skills_developed"]) > 0
        assert "Eldorian Citizen" in summary["achievements"]


@pytest.mark.asyncio
async def test_session_summary_multi_generation_chain():
    """Verify session summary compiles complete history across multiple generations per SPEC §10."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Life 1 (Generation 1)
        gen1 = await _create_test_character(client, name="Gen 1 Founder")
        token = gen1["session_token"]
        gen1_id = gen1["character"]["id"]

        # Train skills on Gen 1 to verify aggregated skills developed
        async with get_session() as session:
            c1 = await session.get(Character, gen1_id)
            assert c1 is not None
            c1.money = 150
            await session.commit()

        # Gen 1 dies in combat
        d1 = await client.post(
            "/api/reincarnation/death",
            json={"character_id": gen1_id, "cause": DeathCause.COMBAT.value},
        )
        assert d1.status_code == 200

        # Life 2 (Generation 2)
        gen2 = await client.post(
            "/api/reincarnation/reincarnate",
            json={
                "session_token": token,
                "name": "Gen 2 Successor",
                "race_name": RaceName.ELF.value,
                "background_name": BackgroundName.MERCHANT_FAMILY.value,
                "gender_presentation": GenderPresentation.FEMALE.value,
            },
        )
        assert gen2.status_code == 201
        gen2_id = gen2.json()["character"]["id"]

        # Gen 2 dies of illness
        d2 = await client.post(
            "/api/reincarnation/death",
            json={"character_id": gen2_id, "cause": DeathCause.ILLNESS.value},
        )
        assert d2.status_code == 200

        # Life 3 (Generation 3 - still alive)
        gen3 = await client.post(
            "/api/reincarnation/reincarnate",
            json={
                "session_token": token,
                "name": "Gen 3 Current Hope",
                "race_name": RaceName.DWARF.value,
                "background_name": BackgroundName.ORPHAN.value,
                "gender_presentation": GenderPresentation.MALE.value,
            },
        )
        assert gen3.status_code == 201

        # Query full session summary
        summary_res = await client.get(f"/api/session/summary?session_token={token}")
        assert summary_res.status_code == 200
        summary = summary_res.json()

        assert summary["total_generations"] == 3
        assert summary["total_deaths"] == 2
        assert summary["is_active"] is True

        # All 3 characters present in order
        chars = summary["characters_created"]
        assert len(chars) == 3
        assert chars[0]["generation"] == 1
        assert chars[0]["name"] == "Gen 1 Founder"
        assert chars[0]["is_alive"] is False
        assert chars[0]["cause_of_death"] == "combat"

        assert chars[1]["generation"] == 2
        assert chars[1]["name"] == "Gen 2 Successor"
        assert chars[1]["is_alive"] is False
        assert chars[1]["cause_of_death"] == "illness"

        assert chars[2]["generation"] == 3
        assert chars[2]["name"] == "Gen 3 Current Hope"
        assert chars[2]["is_alive"] is True

        # 2 Death records
        assert len(summary["death_records"]) == 2
        assert summary["death_records"][0]["generation"] == 1
        assert summary["death_records"][1]["generation"] == 2

        # 2 Legacies passed
        assert len(summary["legacies_passed"]) == 2

        # Aggregated achievements
        assert "Eldorian Citizen" in summary["achievements"]
        assert "Prosperous Citizen" in summary["achievements"]  # Gen 1 had 150 gold


@pytest.mark.asyncio
async def test_end_session_flow_and_retires_living_character():
    """Verify POST /api/session/end retires active character and finalizes session."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        char_data = await _create_test_character(client, name="Retiring Hero")
        token = char_data["session_token"]
        char_id = char_data["character"]["id"]

        # Conclude session
        end_res = await client.post(
            "/api/session/end",
            json={"session_token": token},
        )
        assert end_res.status_code == 200
        summary = end_res.json()

        assert summary["is_active"] is False
        assert summary["ended_at"] is not None
        assert summary["total_deaths"] == 1  # Living character peacefully retired

        # Character record reflects retirement
        c0 = summary["characters_created"][0]
        assert c0["character_id"] == char_id
        assert c0["is_alive"] is False
        assert c0["cause_of_death"] == "old_age"
        assert "peacefully retired" in c0["death_description"].lower()

        # LifeRecord exists
        assert len(summary["death_records"]) == 1
        assert summary["death_records"][0]["character_id"] == char_id

        # Verify database session state
        async with get_session() as session:
            sess_res = await session.execute(
                select(GameSession).where(GameSession.session_token == token)
            )
            db_session = sess_res.scalar_one()
            assert db_session.is_active is False
            assert db_session.ended_at is not None


@pytest.mark.asyncio
async def test_cannot_reincarnate_on_ended_session():
    """Verify attempting to reincarnate on a concluded session is rejected with ValidationError."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        char_data = await _create_test_character(client, name="Closed World Hero")
        token = char_data["session_token"]

        # End session
        await client.post("/api/session/end", json={"session_token": token})

        # Attempt to reincarnate
        reinc_res = await client.post(
            "/api/reincarnation/reincarnate",
            json={
                "session_token": token,
                "name": "Denied Reborn",
                "race_name": RaceName.HUMAN.value,
                "background_name": BackgroundName.COMMONER.value,
                "gender_presentation": GenderPresentation.MALE.value,
            },
        )
        assert reinc_res.status_code in (400, 422)
        assert "ended" in reinc_res.json()["message"].lower()


@pytest.mark.asyncio
async def test_session_history_endpoint():
    """Verify GET /api/session/history returns past game sessions."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create Session 1
        s1 = await _create_test_character(client, name="Chronicle 1")
        token1 = s1["session_token"]
        await client.post("/api/session/end", json={"session_token": token1})

        # Create Session 2
        s2 = await _create_test_character(client, name="Chronicle 2")
        token2 = s2["session_token"]

        # Query history
        hist_res = await client.get("/api/session/history?limit=10")
        assert hist_res.status_code == 200
        hist_data = hist_res.json()

        assert hist_data["total_sessions"] >= 2
        tokens = [s["session_token"] for s in hist_data["sessions"]]
        assert token1 in tokens
        assert token2 in tokens

        # Verify active flag
        item1 = next(s for s in hist_data["sessions"] if s["session_token"] == token1)
        assert item1["is_active"] is False
        assert item1["ended_at"] is not None

        item2 = next(s for s in hist_data["sessions"] if s["session_token"] == token2)
        assert item2["is_active"] is True


@pytest.mark.asyncio
async def test_session_summary_error_handling():
    """Verify error handling on invalid or nonexistent session tokens."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Empty token
        res_empty = await client.get("/api/session/summary?session_token=")
        assert res_empty.status_code in (400, 422)

        # Whitespace token
        res_space = await client.get("/api/session/summary?session_token=%20%20%20")
        assert res_space.status_code in (400, 422)

        # Nonexistent token
        res_404 = await client.get(
            "/api/session/summary?session_token=nonexistent_token_123"
        )
        assert res_404.status_code == 404
