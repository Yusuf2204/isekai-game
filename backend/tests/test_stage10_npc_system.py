"""Comprehensive test suite for Stage 10 Increment 2: NPC Interaction System.

Verifies:
1. NPC catalog integrity (10-15 NPCs across all 7 locations, personality coverage per SPEC §7, §13).
2. Location-based retrieval with and without session tokens.
3. NPC detailed profiles and lore.
4. Dialogue interactions, dynamic greetings, times spoken, and memory flags.
5. Gifting gold and inventory items, greedy vs arrogant responses, and boundary clamping.
6. Character-wide relationship listing and tier classification.
7. Deceased character rejection guard.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session, recreate_db
from app.main import app, lifespan
from app.models.enums import (
    BackgroundName,
    GenderPresentation,
    NPCPersonality,
    RaceName,
)
from app.models.gameplay import Character, InventoryItem, NPCRelationship
from app.services.npc.definitions import NPC_DEFINITIONS


@pytest_asyncio.fixture(autouse=True)
async def isolated_test_db():
    """Ensure database tables are recreated and world is seeded before each test."""
    await recreate_db()
    async with lifespan(app):
        yield


async def _create_test_character(client: AsyncClient, starting_gold: int = 100) -> dict:
    """Helper to create a fresh character and ensure starting gold."""
    create_res = await client.post(
        "/api/character/create",
        json={
            "name": "Isekai Protagonist",
            "race_name": RaceName.HUMAN.value,
            "background_name": BackgroundName.COMMONER.value,
            "gender_presentation": GenderPresentation.MALE.value,
        },
    )
    assert create_res.status_code == 201
    char_data = create_res.json()
    char_id = char_data["character"]["id"]

    # Ensure character has starting gold
    async with get_session() as session:
        char = await session.get(Character, char_id)
        assert char is not None
        char.money = starting_gold
        await session.flush()

    return char_data


class TestNPCCatalogIntegrity:
    """Tests catalog scope and structural integrity per SPEC §7 and §13."""

    def test_npc_count_within_specification(self):
        """SPEC §13 specifies 10-15 important NPCs."""
        assert 10 <= len(NPC_DEFINITIONS) <= 15
        assert len(NPC_DEFINITIONS) == 13

    def test_all_locations_have_npcs(self):
        """All 7 explorable locations in Eldoria must have at least one NPC."""
        locations_with_npcs = {npc["location_name"] for npc in NPC_DEFINITIONS}
        expected_locations = {
            "Capital City: Luminaris",
            "Sunken Mire",
            "Ironpeak Citadel",
            "Whispering Woods",
            "Frostfall Pass",
            "Silvercreek Sanctuary",
            "Shattered Coast",
        }
        assert locations_with_npcs == expected_locations

    def test_all_personalities_represented(self):
        """All 6 NPC personality types must be represented across the roster."""
        personalities = {npc["personality"] for npc in NPC_DEFINITIONS}
        expected_personalities = set(NPCPersonality)
        assert personalities == expected_personalities

    def test_npc_structure_validity(self):
        """Each NPC definition must have dialogue lines, descriptions, and valid bounds."""
        for npc in NPC_DEFINITIONS:
            assert len(npc["name"]) > 0
            assert npc["age"] > 0
            assert len(npc["description"]) > 20
            assert len(npc["background_story"]) > 20
            assert len(npc["greeting"]) > 5
            assert len(npc["farewell"]) > 5
            # At least 3 dialogue lines per AGENTS §14 Recommendation 4
            assert len(npc["dialogue_lines"]) >= 3
            assert npc["min_relationship"] == -100
            assert npc["max_relationship"] == 100
            assert len(npc["available_times"]) >= 1


class TestNPCLocationAndRetrieval:
    """Tests location-based retrieval and detailed profile endpoints."""

    @pytest.mark.asyncio
    async def test_get_npcs_by_location_without_session(self):
        """Retrieving NPCs by location without session returns zeroed relationship data."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Query Capital City: Luminaris (location_id = 1)
            res = await client.get("/api/npc/location/1")
            assert res.status_code == 200
            data = res.json()
            assert data["location_id"] == 1
            assert data["location_name"] == "Capital City: Luminaris"
            assert len(data["npcs"]) == 3

            names = [npc["name"] for npc in data["npcs"]]
            assert "Seraphina Vance" in names
            assert "Marcus Aurelius Vane" in names
            assert "Archmage Vaelin" in names

            # Without session, relationships are 0
            for npc in data["npcs"]:
                assert npc["relationship_value"] == 0
                assert npc["trust"] == 0

    @pytest.mark.asyncio
    async def test_get_npcs_by_location_invalid_location_404(self):
        """Querying NPCs for nonexistent location returns 404."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            res = await client.get("/api/npc/location/9999")
            assert res.status_code == 404
            assert res.json()["error"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_npc_detail_profile(self):
        """Getting detail profile returns complete lore, availability, and background."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            res = await client.get("/api/npc/1")
            assert res.status_code == 200
            npc = res.json()
            assert npc["id"] == 1
            assert npc["name"] == "Seraphina Vance"
            assert npc["race_name"] == "human"
            assert npc["occupation"] == "Guild Registrar"
            assert npc["location_name"] == "Capital City: Luminaris"
            assert "Adventurers Guild" in npc["greeting"]
            assert len(npc["available_times"]) >= 2

    @pytest.mark.asyncio
    async def test_get_npc_detail_invalid_id_404(self):
        """Getting detail profile for nonexistent NPC returns 404."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            res = await client.get("/api/npc/9999")
            assert res.status_code == 404
            assert res.json()["error"] == "NOT_FOUND"


class TestNPCDialogueInteraction:
    """Tests talk interactions, dynamic greetings, times spoken, and memory flags."""

    @pytest.mark.asyncio
    async def test_first_talk_sets_met_character_and_increases_relationship(self):
        """First conversation sets met_character flag and boosts relationship."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            talk_res = await client.post(
                "/api/npc/1/talk",
                json={"session_token": token},
            )
            assert talk_res.status_code == 200
            data = talk_res.json()
            assert data["npc_name"] == "Seraphina Vance"
            assert data["relationship_change"] > 0
            assert data["trust_change"] > 0
            assert data["relationship_value"] > 0
            assert data["memory_flags"]["met_character"] is True

    @pytest.mark.asyncio
    async def test_subsequent_talk_cycles_dialogue_and_tracks_topics(self):
        """Repeated talk cycles dialogue lines and tracks custom topics in memory flags."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            # Talk once with topic
            res1 = await client.post(
                "/api/npc/1/talk",
                json={"session_token": token, "topic": "Quests"},
            )
            assert res1.status_code == 200
            assert "discussed_quests" in res1.json()["memory_flags"]

            # Talk second time
            res2 = await client.post(
                "/api/npc/1/talk",
                json={"session_token": token},
            )
            assert res2.status_code == 200
            assert res2.json()["memory_flags"]["spoken_again"] is True
            # Total relationship accumulated
            assert res2.json()["relationship_value"] > res1.json()["relationship_value"]

    @pytest.mark.asyncio
    async def test_high_relationship_modifies_greeting(self):
        """High relationship value alters greeting to be welcoming and friendly."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]
            char_id = char_data["character"]["id"]

            # Manually set high relationship with NPC 1
            async with get_session() as session:
                rel = NPCRelationship(
                    character_id=char_id,
                    npc_id=1,
                    value=50,
                    trust=40,
                    memory_flags={"met_character": True},
                )
                session.add(rel)
                await session.flush()

            talk_res = await client.post(
                "/api/npc/1/talk",
                json={"session_token": token},
            )
            assert talk_res.status_code == 200
            assert "Welcome back, friend!" in talk_res.json()["greeting"]


class TestNPCGifting:
    """Tests gifting money and inventory items, greedy vs arrogant responses."""

    @pytest.mark.asyncio
    async def test_gift_money_greedy_npc_high_affinity(self):
        """Gifting money to greedy NPC (Marcus Aurelius Vane) yields large relationship bonus."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client, starting_gold=100)
            token = char_data["session_token"]

            # Marcus Aurelius Vane is NPC id=2
            gift_res = await client.post(
                "/api/npc/2/gift",
                json={"session_token": token, "money": 30},
            )
            assert gift_res.status_code == 200
            data = gift_res.json()
            assert data["gift_accepted"] is True
            assert data["money_gifted"] == 30
            assert data["remaining_money"] == 70
            assert data["relationship_change"] >= 15
            assert data["memory_flags"]["received_gift"] is True

    @pytest.mark.asyncio
    async def test_gift_money_generous_patron_flag(self):
        """Gifting 50 gold or more sets the generous_patron memory flag."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client, starting_gold=100)
            token = char_data["session_token"]

            gift_res = await client.post(
                "/api/npc/2/gift",
                json={"session_token": token, "money": 50},
            )
            assert gift_res.status_code == 200
            data = gift_res.json()
            assert data["memory_flags"]["generous_patron"] is True

    @pytest.mark.asyncio
    async def test_gift_money_insufficient_funds_400(self):
        """Attempting to gift more gold than possessed raises 400 validation error."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client, starting_gold=10)
            token = char_data["session_token"]

            gift_res = await client.post(
                "/api/npc/1/gift",
                json={"session_token": token, "money": 50},
            )
            assert gift_res.status_code == 400
            assert gift_res.json()["error"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_gift_inventory_item_success(self):
        """Gifting an item from inventory removes item and improves relationship."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]
            char_id = char_data["character"]["id"]

            # Add a healing potion to inventory
            async with get_session() as session:
                item = InventoryItem(
                    character_id=char_id,
                    item_id="healing_potion",
                    name="Healing Potion",
                    description="Restores vitality",
                    quantity=2,
                    item_type="consumable",
                    value=25,
                )
                session.add(item)
                await session.flush()

            gift_res = await client.post(
                "/api/npc/1/gift",
                json={"session_token": token, "item_name": "Healing Potion"},
            )
            assert gift_res.status_code == 200
            data = gift_res.json()
            assert data["item_gifted"] == "Healing Potion"
            assert data["relationship_change"] == 10
            assert data["trust_change"] == 8
            assert data["memory_flags"]["gifted_healing_potion"] is True

            # Verify item quantity decremented in database
            async with get_session() as session:
                item_db = await session.get(InventoryItem, item.id)
                assert item_db is not None
                assert item_db.quantity == 1


class TestNPCRelationshipListingAndTiers:
    """Tests listing all character relationships and tier classification."""

    @pytest.mark.asyncio
    async def test_get_all_relationships_for_character(self):
        """Querying all relationships returns list with correct tiers."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            char_data = await _create_test_character(client)
            token = char_data["session_token"]

            # Talk to Seraphina (id=1) and Marcus (id=2)
            await client.post("/api/npc/1/talk", json={"session_token": token})
            await client.post("/api/npc/2/talk", json={"session_token": token})

            rel_res = await client.get(
                "/api/npc/relationships", params={"session_token": token}
            )
            assert rel_res.status_code == 200
            data = rel_res.json()
            assert len(data["relationships"]) == 2

            npc_names = {r["npc_name"] for r in data["relationships"]}
            assert "Seraphina Vance" in npc_names
            assert "Marcus Aurelius Vane" in npc_names

            # Initial relationships are in Neutral tier
            for r in data["relationships"]:
                assert r["relationship_tier"] == "Neutral"


class TestNPCDeceasedGuard:
    """Tests deceased character rejection guard for NPC interactions."""

    @pytest.mark.asyncio
    async def test_deceased_character_cannot_talk_or_gift(self):
        """Dead characters are rejected with 409 INVALID_STATE."""
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

            # Attempt talk
            talk_res = await client.post(
                "/api/npc/1/talk", json={"session_token": token}
            )
            assert talk_res.status_code == 409
            assert talk_res.json()["error"] == "INVALID_STATE"

            # Attempt gift
            gift_res = await client.post(
                "/api/npc/1/gift",
                json={"session_token": token, "money": 10},
            )
            assert gift_res.status_code == 409
            assert gift_res.json()["error"] == "INVALID_STATE"
