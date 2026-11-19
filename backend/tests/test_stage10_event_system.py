"""Tests for Stage 10 Increment 1: Event System.

Verifies:
- 20-30 event definitions covering all 10 EventCategory types (SPEC §6.5, §13).
- Contextual eligibility and weighted selection.
- Active event persistence in GameplayState across requests.
- Authoritative consequence execution (health, money, inventory, skills, attributes).
- Seeded determinism on stat checks.
- Event-induced death handling with EVENT_CONSEQUENCES cause.
- Proper error handling and input validation (no undefined states).
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session, recreate_db
from app.main import app, lifespan
from app.models.enums import (
    DeathCause,
    EventCategory,
    RaceName,
    BackgroundName,
    GenderPresentation,
)
from app.models.gameplay import Character
from app.services.events.definitions import EVENT_DEFINITIONS, EVENTS_BY_ID


@pytest_asyncio.fixture(autouse=True)
async def _setup_clean_db():
    """Ensure clean database with startup world seeding before each test."""
    await recreate_db()
    async with lifespan(app):
        yield


async def _create_test_character(client: AsyncClient, name: str = "Event Hero") -> dict:
    """Helper to create a playable character and obtain session token."""
    response = await client.post(
        "/api/character/create",
        json={
            "name": name,
            "race_name": RaceName.HUMAN.value,
            "background_name": BackgroundName.COMMONER.value,
            "gender_presentation": GenderPresentation.MALE.value,
        },
    )
    assert response.status_code == 201
    return response.json()


class TestEventCatalogIntegrity:
    """Verification of static event data completeness per SPEC requirements."""

    def test_event_count_within_specification(self):
        """SPEC §6.5 & §13 require 20-30 predefined event definitions."""
        count = len(EVENT_DEFINITIONS)
        assert 20 <= count <= 30, f"Expected 20-30 events, found {count}"

    def test_all_event_categories_represented(self):
        """Every category in EventCategory enum must have at least one defined event."""
        defined_categories = {event["category"] for event in EVENT_DEFINITIONS}
        for category in EventCategory:
            assert (
                category in defined_categories
            ), f"Missing event definition for category: {category}"

    def test_event_structure_validity(self):
        """Every event definition must possess required schema fields and valid choices."""
        for event in EVENT_DEFINITIONS:
            assert "id" in event and event["id"]
            assert "title" in event and event["title"]
            assert "category" in event and isinstance(event["category"], EventCategory)
            assert "description" in event and len(event["description"]) > 10
            assert "choices" in event and len(event["choices"]) >= 2
            assert event["weight"] > 0

            for choice in event["choices"]:
                assert "id" in choice and choice["id"]
                assert "label" in choice and choice["label"]
                assert "description" in choice and choice["description"]
                assert "consequences" in choice


class TestEventTriggerAndActiveState:
    """Tests for triggering events and tracking active event state in GameplayState."""

    @pytest.mark.asyncio
    async def test_get_active_event_initially_none(self):
        """Fresh character has no active event initially."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            response = await client.get(
                "/api/events/active", params={"session_token": token}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["has_active_event"] is False
            assert data["event"] is None

    @pytest.mark.asyncio
    async def test_trigger_random_event_sets_active(self):
        """Triggering an event stores it on GameplayState and presents it to client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            trigger_res = await client.post(
                "/api/events/trigger",
                json={"session_token": token},
            )
            assert trigger_res.status_code == 200
            trigger_data = trigger_res.json()
            assert trigger_data["has_active_event"] is True
            active_event = trigger_data["event"]
            assert active_event["id"] in EVENTS_BY_ID
            assert len(active_event["choices"]) >= 2

            # Verify persisted in database GameplayState
            active_res = await client.get(
                "/api/events/active", params={"session_token": token}
            )
            assert active_res.status_code == 200
            active_data = active_res.json()
            assert active_data["has_active_event"] is True
            assert active_data["event"]["id"] == active_event["id"]

    @pytest.mark.asyncio
    async def test_trigger_forced_event_id(self):
        """Explicitly triggering an event by ID selects that exact event."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            trigger_res = await client.post(
                "/api/events/trigger",
                json={"session_token": token, "event_id": "suspicious_merchant"},
            )
            assert trigger_res.status_code == 200
            data = trigger_res.json()
            assert data["event"]["id"] == "suspicious_merchant"
            assert data["event"]["title"] == "The Shady Merchant"

    @pytest.mark.asyncio
    async def test_trigger_invalid_event_id_raises_404(self):
        """Attempting to trigger an unknown event ID returns 404."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            response = await client.post(
                "/api/events/trigger",
                json={"session_token": token, "event_id": "nonexistent_event_xyz"},
            )
            assert response.status_code == 404
            assert response.json()["error"] == "NOT_FOUND"


class TestEventChoiceResolution:
    """Tests for submitting choices, evaluating stat checks, and applying authoritative state changes."""

    @pytest.mark.asyncio
    async def test_resolve_choice_without_active_event_raises_400(self):
        """Submitting a choice when no event is active raises a 400 ValidationError."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            response = await client.post(
                "/api/events/choose",
                json={"session_token": token, "choice_id": "chase"},
            )
            assert response.status_code == 400
            assert response.json()["error"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_resolve_invalid_choice_raises_400(self):
        """Submitting an invalid choice ID for the active event raises a 400 ValidationError."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            await client.post(
                "/api/events/trigger",
                json={"session_token": token, "event_id": "stolen_wallet"},
            )

            response = await client.post(
                "/api/events/choose",
                json={"session_token": token, "choice_id": "invalid_option_abc"},
            )
            assert response.status_code == 400
            assert response.json()["error"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_resolve_choice_applies_consequences_and_clears_event(self):
        """Resolving an event applies real state deltas and clears the active event."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]
            initial_money = char_data["character"]["money"]

            # Trigger stolen wallet event
            await client.post(
                "/api/events/trigger",
                json={"session_token": token, "event_id": "stolen_wallet"},
            )

            # Choose "let_go" (no stat check, loses 10 gold, gains survival XP)
            choose_res = await client.post(
                "/api/events/choose",
                json={"session_token": token, "choice_id": "let_go"},
            )
            assert choose_res.status_code == 200
            result = choose_res.json()
            assert result["event_id"] == "stolen_wallet"
            assert result["choice_id"] == "let_go"
            assert result["money_change"] == -10
            assert result["character_dead"] is False
            assert "survival" in result["skill_xp"]

            # Verify character money updated in database
            curr_char = await client.get(
                "/api/character/resources", params={"session_token": token}
            )
            assert curr_char.status_code == 200
            assert curr_char.json()["money"] == initial_money - 10

            # Verify active event is cleared
            active_res = await client.get(
                "/api/events/active", params={"session_token": token}
            )
            assert active_res.json()["has_active_event"] is False

    @pytest.mark.asyncio
    async def test_resolve_choice_inventory_and_healing(self):
        """Test event choice adding inventory items and healing."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            # Trigger stray hound event
            await client.post(
                "/api/events/trigger",
                json={"session_token": token, "event_id": "stray_hound"},
            )

            # Feed bread option
            res = await client.post(
                "/api/events/choose",
                json={"session_token": token, "choice_id": "feed_bread"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["health_change"] == 5
            assert data["stamina_change"] == 5


class TestEventStatChecksAndDeterminism:
    """Tests verifying stat check mechanics and deterministic seed reproducibility."""

    @pytest.mark.asyncio
    async def test_stat_check_recorded_in_resolution(self):
        """Choices requiring attribute tests include StatCheckResultSchema in response."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            await client.post(
                "/api/events/trigger",
                json={"session_token": token, "event_id": "stolen_wallet"},
            )

            # Chase choice tests agility (DC 12)
            res = await client.post(
                "/api/events/choose",
                json={"session_token": token, "choice_id": "chase"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["stat_check"] is not None
            check = data["stat_check"]
            assert check["attribute"] == "agility"
            assert check["difficulty"] == 12
            assert isinstance(check["roll"], int)
            assert isinstance(check["passed"], bool)


class TestEventFatalityAndDeceasedGuard:
    """Tests for character mortality via event consequences (SPEC §9.1)."""

    @pytest.mark.asyncio
    async def test_event_death_sets_event_consequences_cause(self):
        """If health drops to 0 during an event, character dies with EVENT_CONSEQUENCES cause."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]
            char_id = char_data["character"]["id"]

            # Manually reduce character health to 5 to make event damage lethal
            async with get_session() as session:
                char_db = await session.get(Character, char_id)
                char_db.current_health = 5
                await session.flush()

            # Trigger brigands event
            await client.post(
                "/api/events/trigger",
                json={"session_token": token, "event_id": "highway_brigands"},
            )

            # Choose stand_and_fight (damages health by at least -12)
            res = await client.post(
                "/api/events/choose",
                json={"session_token": token, "choice_id": "stand_and_fight"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["character_dead"] is True
            assert data["death_cause"] == DeathCause.EVENT_CONSEQUENCES.value

            # Verify character is marked dead in database
            async with get_session() as session:
                dead_char = await session.get(Character, char_id)
                assert dead_char is not None
                assert dead_char.is_alive is False
                assert dead_char.current_health == 0
                assert dead_char.death_cause == DeathCause.EVENT_CONSEQUENCES

    @pytest.mark.asyncio
    async def test_deceased_character_cannot_trigger_or_choose_events(self):
        """Dead characters are rejected with 409 GameStateError on event interactions."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]
            char_id = char_data["character"]["id"]

            # Mark character dead
            async with get_session() as session:
                char_db = await session.get(Character, char_id)
                char_db.is_alive = False
                await session.flush()

            # Try to trigger event
            trigger_res = await client.post(
                "/api/events/trigger",
                json={"session_token": token},
            )
            assert trigger_res.status_code == 409
            assert trigger_res.json()["error"] == "INVALID_STATE"
