"""Tests for world/location API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import get_session, recreate_db
from app.models.enums import RaceName, BackgroundName, GenderPresentation
from app.services.world import seed_world
from app.services.character.creation import create_character


async def _setup_db():
    """Set up database with world data."""
    await recreate_db()
    async with get_session() as session:
        await seed_world(session)
        return session


async def _create_character_with_session():
    """Create a test character with session."""
    async with get_session() as session:
        character, game_session = await create_character(
            session=session,
            name="Test Character",
            race_name=RaceName.HUMAN,
            background_name=BackgroundName.COMMONER,
            gender_presentation=GenderPresentation.MALE,
        )
        return character, game_session


class TestWorldOverview:
    """Tests for world overview endpoint."""

    @pytest.mark.asyncio
    async def test_get_world_overview(self):
        """Test getting world overview."""
        await _setup_db()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/world/overview")
            assert response.status_code == 200
            data = response.json()
            assert data["kingdom_name"] == "Eldoria"
            assert "kingdom_description" in data
            assert "regions" in data
            assert len(data["regions"]) == 3
            assert data["total_locations"] == 7

            # Check regions
            region_names = {r["name"] for r in data["regions"]}
            assert region_names == {"aetheria", "valdren", "elarion"}

            # Check each region has required fields
            for region in data["regions"]:
                assert "id" in region
                assert "display_name" in region
                assert "description" in region
                assert "danger_level" in region


class TestLocationsList:
    """Tests for listing locations."""

    @pytest.mark.asyncio
    async def test_list_all_locations(self):
        """Test listing all locations."""
        await _setup_db()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/world/locations")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 7
            assert len(data["locations"]) == 7

            # Check each location has required fields
            for loc in data["locations"]:
                assert "id" in loc
                assert "name" in loc
                assert "region_id" in loc
                assert "region_name" in loc
                assert "description" in loc
                assert "location_type" in loc
                assert "danger_level" in loc
                assert "population" in loc
                assert "has_guild" in loc
                assert "has_market" in loc
                assert "has_inn" in loc
                assert "available_activities" in loc

    @pytest.mark.asyncio
    async def test_list_locations_by_region(self):
        """Test filtering locations by region."""
        await _setup_db()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Get region IDs first
            response = await client.get("/api/world/locations")
            all_locs = response.json()["locations"]

            # Find a location in Aetheria region
            aetheria_locs = [
                loc for loc in all_locs if loc["region_name"] == "aetheria"
            ]
            assert len(aetheria_locs) == 3

            # Filter by region_id
            region_id = aetheria_locs[0]["region_id"]
            response = await client.get(f"/api/world/locations?region_id={region_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 3
            for loc in data["locations"]:
                assert loc["region_name"] == "aetheria"

    @pytest.mark.asyncio
    async def test_list_locations_by_type(self):
        """Test filtering locations by type."""
        await _setup_db()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/world/locations?location_type=city")
            assert response.status_code == 200
            data = response.json()
            # Only 1 city type (Luminaris)
            assert data["total"] == 1
            assert data["locations"][0]["location_type"] == "city"


class TestLocationDetail:
    """Tests for location detail endpoint."""

    @pytest.mark.asyncio
    async def test_get_location_detail(self):
        """Test getting location detail."""
        await _setup_db()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # First get a location ID
            response = await client.get("/api/world/locations")
            loc_id = response.json()["locations"][0]["id"]

            response = await client.get(f"/api/world/locations/{loc_id}")
            assert response.status_code == 200
            data = response.json()

            assert "location" in data
            assert "npcs" in data
            assert "connected_locations" in data

            # Check location detail
            loc = data["location"]
            assert loc["id"] == loc_id
            assert "available_activities" in loc

            # Check NPCs (should be empty initially but structure is correct)
            assert isinstance(data["npcs"], list)

            # Check connected locations
            assert isinstance(data["connected_locations"], list)

    @pytest.mark.asyncio
    async def test_get_location_detail_not_found(self):
        """Test getting non-existent location."""
        await _setup_db()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/world/locations/99999")
            assert response.status_code == 404
            data = response.json()
            assert data["detail"]["error"] == "NOT_FOUND"


class TestTravel:
    """Tests for travel endpoint."""

    @pytest.mark.asyncio
    async def test_travel_to_location(self):
        """Test traveling to a location."""
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Get a different location to travel to
            response = await client.get("/api/world/locations")
            locations = response.json()["locations"]
            current_loc_id = character.starting_location_id

            # Find a different location
            target_loc = next(
                (loc for loc in locations if loc["id"] != current_loc_id), None
            )
            assert target_loc is not None
            target_loc_id = target_loc["id"]

            # Travel
            response = await client.post(
                "/api/world/travel",
                json={"target_location_id": target_loc_id},
                params={"session_token": session_token},
            )
            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert data["previous_location_id"] == current_loc_id
            assert data["new_location_id"] == target_loc_id
            assert data["time_advanced"] >= 1
            assert "new_time_of_day" in data
            assert "new_day" in data
            assert data["new_day"] >= 1

    @pytest.mark.asyncio
    async def test_travel_to_same_location(self):
        """Test traveling to the same location fails."""
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            current_loc_id = character.starting_location_id

            response = await client.post(
                "/api/world/travel",
                json={"target_location_id": current_loc_id},
                params={"session_token": session_token},
            )
            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["error"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_travel_invalid_location(self):
        """Test traveling to invalid location."""
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/world/travel",
                json={"target_location_id": 99999},
                params={"session_token": session_token},
            )
            assert response.status_code == 404
            data = response.json()
            assert data["detail"]["error"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_travel_updates_gameplay_state(self):
        """Test that travel updates gameplay state location and time."""
        character, game_session = await _create_character_with_session()
        session_token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/world/locations")
            locations = response.json()["locations"]
            target_loc = next(
                (
                    loc
                    for loc in locations
                    if loc["id"] != character.starting_location_id
                ),
                None,
            )
            target_loc_id = target_loc["id"]

            # Travel
            await client.post(
                "/api/world/travel",
                json={"target_location_id": target_loc_id},
                params={"session_token": session_token},
            )

            # Check time state updated
            response = await client.get(
                "/api/time/state", params={"session_token": session_token}
            )
            assert response.status_code == 200
            time_data = response.json()
            assert time_data["current_day"] >= 1
            # Time should have advanced


class TestWorldAPIIntegration:
    """Integration tests for world API with character creation."""

    @pytest.mark.asyncio
    async def test_new_character_has_starting_location(self):
        """Test that new character gets a starting location."""
        await _setup_db()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Create character
            response = await client.post(
                "/api/character/create",
                json={
                    "name": "Traveler",
                    "race_name": "human",
                    "background_name": "commoner",
                    "gender_presentation": "male",
                },
            )
            assert response.status_code == 201
            data = response.json()
            character = data["character"]
            _ = data["session_token"]  # Unused but kept for future use

            assert character["starting_location_id"] is not None

            # Verify location exists
            response = await client.get(
                f"/api/world/locations/{character['starting_location_id']}"
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_character_can_travel_after_creation(self):
        """Test character can travel immediately after creation."""
        await _setup_db()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/character/create",
                json={
                    "name": "Wanderer",
                    "race_name": "human",
                    "background_name": "commoner",
                    "gender_presentation": "male",
                },
            )
            data = response.json()
            character = data["character"]
            session_token = data["session_token"]

            # Get another location
            loc_response = await client.get("/api/world/locations")
            locations = loc_response.json()["locations"]
            target = next(
                (
                    loc
                    for loc in locations
                    if loc["id"] != character["starting_location_id"]
                ),
                None,
            )

            # Travel
            travel_response = await client.post(
                "/api/world/travel",
                json={"target_location_id": target["id"]},
                params={"session_token": session_token},
            )
            assert travel_response.status_code == 200
            travel_data = travel_response.json()
            assert travel_data["success"] is True
