"""Tests for Stage 5: Inventory and Treatment Consolidation.

Verifies:
- Item identity consistency: use_item validates and consumes by item_id (CB-05).
- Single canonical namespace for conditions & treatments under /api/conditions (CB-19).
- Single canonical TreatmentRequest and TreatmentResponse schemas (CB-19).
- Removed duplicate routes return 404 (CB-19).
- Inventory service helpers function correctly without variable collisions (F823).
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import get_session, recreate_db
from app.core.exceptions import ResourceError
from app.models.enums import BackgroundName, GenderPresentation, RaceName
from app.models.gameplay import Character, InventoryItem
from app.services.character.creation import create_character
from app.services.character.conditions import add_condition
from app.services.character.inventory import (
    add_item,
    get_available_treatments_for_condition,
    validate_character_inventory,
)
from app.services.world import seed_world


async def _setup_db():
    """Set up database with world data."""
    await recreate_db()
    async with get_session() as session:
        await seed_world(session)


@pytest_asyncio.fixture(autouse=True)
async def _prepared_database():
    """Recreate and seed the test database before each test."""
    await _setup_db()


async def _create_test_character():
    """Helper to create a test character and session."""
    async with get_session() as session:
        character, game_session = await create_character(
            session=session,
            name="Stage5 Hero",
            race_name=RaceName.HUMAN,
            background_name=BackgroundName.COMMONER,
            gender_presentation=GenderPresentation.MALE,
        )
        return character, game_session


class TestItemIdentityAndUsage:
    """Tests for item identity consistency and /api/character/inventory/use (CB-05)."""

    @pytest.mark.asyncio
    async def test_use_item_by_item_id_success(self):
        """Test consuming an item by item_id decrements quantity correctly."""
        character, game_session = await _create_test_character()

        # Add consumable item to inventory
        async with get_session() as session:
            db_char = await session.get(type(character), character.id)
            await add_item(
                session,
                db_char,
                item_name="Health Potion",
                quantity=3,
                value=25,
                item_type="consumable",
                item_id="potion_healing",
            )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/character/inventory/use",
                params={"session_token": game_session.session_token},
                json={"item_id": "potion_healing", "quantity": 1},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Health Potion" in data["message"]
            assert data["item_consumed"]["item_id"] == "potion_healing"
            assert data["item_consumed"]["previous_quantity"] == 3
            assert data["item_consumed"]["new_quantity"] == 2
            assert data["item_consumed"]["fully_removed"] is False

            # Verify through GET /api/character/inventory
            inv_resp = await client.get(
                "/api/character/inventory",
                params={"session_token": game_session.session_token},
            )
            assert inv_resp.status_code == 200
            inv_data = inv_resp.json()
            potion = next(
                i for i in inv_data["inventory"] if i["item_id"] == "potion_healing"
            )
            assert potion["quantity"] == 2

    @pytest.mark.asyncio
    async def test_use_item_authoritative_on_item_id(self):
        """Test that item_id is authoritative even if item_name differs or is omitted."""
        character, game_session = await _create_test_character()

        async with get_session() as session:
            db_char = await session.get(type(character), character.id)
            await add_item(
                session,
                db_char,
                item_name="True Elixir",
                quantity=2,
                item_type="consumable",
                item_id="elixir_01",
            )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Pass mismatched item_name; item_id must dictate consumption
            response = await client.post(
                "/api/character/inventory/use",
                params={"session_token": game_session.session_token},
                json={
                    "item_id": "elixir_01",
                    "item_name": "Completely Wrong Name",
                    "quantity": 1,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["item_consumed"]["item_id"] == "elixir_01"
            assert data["item_consumed"]["name"] == "True Elixir"

    @pytest.mark.asyncio
    async def test_use_item_depletes_and_removes(self):
        """Test that using the last quantity removes the item from inventory."""
        character, game_session = await _create_test_character()

        async with get_session() as session:
            db_char = await session.get(type(character), character.id)
            await add_item(
                session,
                db_char,
                item_name="Bread",
                quantity=1,
                item_type="consumable",
                item_id="food_bread",
            )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/character/inventory/use",
                params={"session_token": game_session.session_token},
                json={"item_id": "food_bread", "quantity": 1},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["item_consumed"]["fully_removed"] is True
            assert data["item_consumed"]["new_quantity"] == 0

            # Verify it's no longer in inventory
            inv_resp = await client.get(
                "/api/character/inventory",
                params={"session_token": game_session.session_token},
            )
            inv_data = inv_resp.json()
            assert not any(i["item_id"] == "food_bread" for i in inv_data["inventory"])

    @pytest.mark.asyncio
    async def test_use_item_insufficient_or_missing_returns_400(self):
        """Test that insufficient quantity or missing item returns HTTP 400 ResourceError."""
        character, game_session = await _create_test_character()

        async with get_session() as session:
            db_char = await session.get(type(character), character.id)
            await add_item(
                session,
                db_char,
                item_name="Apple",
                quantity=1,
                item_type="consumable",
                item_id="food_apple",
            )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Request more than available
            resp_too_many = await client.post(
                "/api/character/inventory/use",
                params={"session_token": game_session.session_token},
                json={"item_id": "food_apple", "quantity": 5},
            )
            assert resp_too_many.status_code == 400
            assert resp_too_many.json()["detail"]["error"] == "VALIDATION_ERROR"

            # Request non-existent item
            resp_missing = await client.post(
                "/api/character/inventory/use",
                params={"session_token": game_session.session_token},
                json={"item_id": "nonexistent_potion", "quantity": 1},
            )
            assert resp_missing.status_code == 400
            assert resp_missing.json()["detail"]["error"] == "VALIDATION_ERROR"


class TestCanonicalConditionsAndTreatments:
    """Tests for canonical routes under /api/conditions and duplicate route removal (CB-19)."""

    @pytest.mark.asyncio
    async def test_canonical_condition_endpoints(self):
        """Test /api/conditions/ and definitions endpoints."""
        character, game_session = await _create_test_character()

        # Add condition
        async with get_session() as session:
            db_char = await session.get(type(character), character.id)
            await add_condition(session, db_char, "minor_cut")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # List character conditions
            resp_conds = await client.get(
                "/api/conditions/",
                params={"session_token": game_session.session_token},
            )
            assert resp_conds.status_code == 200
            conds_data = resp_conds.json()
            assert any(c["id"] == "minor_cut" for c in conds_data["conditions"])

            # Condition definitions
            resp_defs = await client.get("/api/conditions/definitions")
            assert resp_defs.status_code == 200
            defs_data = resp_defs.json()
            assert any(c["id"] == "minor_cut" for c in defs_data["conditions"])

            # Treatment definitions
            resp_treats = await client.get("/api/conditions/treatments")
            assert resp_treats.status_code == 200
            treats_data = resp_treats.json()
            assert any(t["id"] == "bandage" for t in treats_data["treatments"])

    @pytest.mark.asyncio
    async def test_canonical_available_treatments_for_condition(self):
        """Test GET /api/conditions/{condition_id}/treatments returns accurate in_inventory flags."""
        character, game_session = await _create_test_character()

        # Add condition minor_cut (treatable by bandage and healing_herbs)
        async with get_session() as session:
            db_char = await session.get(type(character), character.id)
            await add_condition(session, db_char, "minor_cut")
            # Give character bandage but not healing_herbs
            await add_item(
                session,
                db_char,
                item_name="Bandage",
                quantity=2,
                item_id="bandage",
            )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/conditions/minor_cut/treatments",
                params={"session_token": game_session.session_token},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["condition_id"] == "minor_cut"

            treatments = {t["treatment_id"]: t for t in data["available_treatments"]}
            assert "bandage" in treatments
            assert treatments["bandage"]["in_inventory"] is True
            assert "healing_herbs" in treatments
            assert treatments["healing_herbs"]["in_inventory"] is False

    @pytest.mark.asyncio
    async def test_canonical_treat_condition_with_item_consumed(self):
        """Test POST /api/conditions/treat executes atomically and includes item_consumed."""
        character, game_session = await _create_test_character()

        async with get_session() as session:
            db_char = await session.get(type(character), character.id)
            await add_condition(session, db_char, "minor_cut")
            db_char.conditions["minor_cut"]["duration"] = 1
            from sqlalchemy.orm.attributes import flag_modified

            flag_modified(db_char, "conditions")
            await add_item(
                session,
                db_char,
                item_name="Bandage",
                quantity=1,
                item_id="bandage",
            )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/conditions/treat",
                params={"session_token": game_session.session_token},
                json={"condition_id": "minor_cut", "treatment_id": "bandage"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["removed"] is True
            assert data["treatment_used"] == "Bandage"
            assert data["item_consumed"] is not None
            assert data["item_consumed"]["item_id"] == "bandage"
            assert data["item_consumed"]["fully_removed"] is True

            # Verify condition is removed
            cond_resp = await client.get(
                "/api/conditions/",
                params={"session_token": game_session.session_token},
            )
            assert not any(
                c["id"] == "minor_cut" for c in cond_resp.json()["conditions"]
            )

    @pytest.mark.asyncio
    async def test_canonical_treat_condition_missing_item_returns_400(self):
        """Test POST /api/conditions/treat without item in inventory returns 400 Bad Request."""
        character, game_session = await _create_test_character()

        async with get_session() as session:
            db_char = await session.get(type(character), character.id)
            await add_condition(session, db_char, "minor_cut")
            # Do NOT add bandage to inventory

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/conditions/treat",
                params={"session_token": game_session.session_token},
                json={"condition_id": "minor_cut", "treatment_id": "bandage"},
            )
            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["error"] == "VALIDATION_ERROR"
            assert "don't have" in data["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_duplicate_routes_removed_return_404(self):
        """Test that former duplicate routes in /api/character have been removed."""
        character, game_session = await _create_test_character()
        token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 1. /api/character/conditions
            resp1 = await client.get(
                "/api/character/conditions",
                params={"session_token": token},
            )
            assert resp1.status_code == 404

            # 2. /api/character/treatments
            resp2 = await client.get(
                "/api/character/treatments",
                params={"session_token": token},
            )
            assert resp2.status_code == 404

            # 3. /api/character/conditions/{id}/treatments
            resp3 = await client.get(
                "/api/character/conditions/minor_cut/treatments",
                params={"session_token": token},
            )
            assert resp3.status_code == 404

            # 4. /api/character/conditions/{id}/treat
            resp4 = await client.post(
                "/api/character/conditions/minor_cut/treat",
                params={"session_token": token},
                json={"treatment_id": "bandage"},
            )
            assert resp4.status_code == 404


class TestInventoryServiceIntegrity:
    """Tests for inventory service functions and validations."""

    @pytest.mark.asyncio
    async def test_get_available_treatments_service_no_collision(self):
        """Test get_available_treatments_for_condition has no local variable shadowing bug."""
        character, _ = await _create_test_character()

        async with get_session() as session:
            db_char = await session.get(type(character), character.id)
            # Call service function for deep_wound
            treatments = await get_available_treatments_for_condition(
                session, db_char, "deep_wound"
            )
            assert len(treatments) > 0
            # Bandage is a valid treatment for deep_wound
            bandage_entry = next(
                t for t in treatments if t["treatment_id"] == "bandage"
            )
            assert bandage_entry["in_inventory"] is False

    @pytest.mark.asyncio
    async def test_validate_character_inventory(self):
        """Test validate_character_inventory rejects invalid quantities and negative values."""
        char = Character(
            id=999,
            session_id=999,
            generation=1,
            name="Val Hero",
            race_name=RaceName.HUMAN,
            background_name=BackgroundName.COMMONER,
            gender_presentation=GenderPresentation.MALE,
        )

        item_invalid_qty = InventoryItem(
            character_id=999,
            item_id="bad_qty",
            name="Bad Item",
            quantity=0,
            value=10,
        )
        char.inventory = [item_invalid_qty]
        with pytest.raises(ResourceError, match="quantity must be positive"):
            await validate_character_inventory(char)

        item_invalid_val = InventoryItem(
            character_id=999,
            item_id="bad_val",
            name="Bad Val Item",
            quantity=1,
            value=-5,
        )
        char.inventory = [item_invalid_val]
        with pytest.raises(ResourceError, match="cannot be negative"):
            await validate_character_inventory(char)
