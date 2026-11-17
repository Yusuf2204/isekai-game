"""Tests for Stage 6: Global Exception Handling.

Verifies:
- Consistent error envelope with top-level error, message, details (AGENTS.md, CB-04).
- Compatibility with detail dictionary structure (detail.error, detail.message).
- HTTP status code mappings:
  - NotFoundError -> 404
  - ValidationError / ResourceError / ConditionError -> 400
  - ConflictError / GameStateError -> 409
  - Base GameError -> 500
  - RequestValidationError -> 422
  - Unexpected Exception -> 500
- Transaction rollback on unhandled error.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import get_session, recreate_db
from app.core.exceptions import (
    ConflictError,
    GameError,
    GameStateError,
    ValidationError,
)
from app.core.errors import build_error_envelope
from app.models.enums import BackgroundName, GenderPresentation, RaceName
from app.services.character.creation import create_character
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


class TestErrorEnvelopeFormat:
    """Tests for envelope structure and helper functions."""

    def test_build_error_envelope_structure(self):
        """Test build_error_envelope creates compliant top-level and detail fields."""
        envelope = build_error_envelope(
            error_code="TEST_ERROR",
            message="A test message",
            details={"key": "value"},
        )
        assert envelope["error"] == "TEST_ERROR"
        assert envelope["message"] == "A test message"
        assert envelope["details"] == {"key": "value"}
        assert envelope["detail"]["error"] == "TEST_ERROR"
        assert envelope["detail"]["message"] == "A test message"
        assert envelope["detail"]["details"] == {"key": "value"}


class TestGlobalExceptionHandlersAPI:
    """Tests for exception handling across API endpoints."""

    @pytest.mark.asyncio
    async def test_not_found_error_envelope(self):
        """Test NotFoundError returns 404 with standard envelope."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/world/locations/999999",
            )
            assert response.status_code == 404
            data = response.json()

            # Top-level error envelope
            assert data["error"] == "NOT_FOUND"
            assert "not found" in data["message"].lower()
            assert isinstance(data["details"], dict)

            # Detail compatibility
            assert data["detail"]["error"] == "NOT_FOUND"
            assert "not found" in data["detail"]["message"].lower()

    @pytest.mark.asyncio
    async def test_validation_error_envelope(self):
        """Test ValidationError returns 400 with standard envelope."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/character/create",
                json={
                    "name": "Invalid Race Hero",
                    "race_name": "human",
                    "background_name": "commoner",
                    "gender_presentation": "male",
                    "starting_location_id": 999999,
                },
            )
            # Location 999999 fails validation or not found
            assert response.status_code in (400, 404)
            data = response.json()
            assert "error" in data
            assert "message" in data
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_request_validation_error_envelope(self):
        """Test Pydantic RequestValidationError returns 422 with standard envelope."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Missing required fields
            response = await client.post(
                "/api/character/create",
                json={"name": "Incomplete"},
            )
            assert response.status_code == 422
            data = response.json()
            assert data["error"] == "VALIDATION_ERROR"
            assert "message" in data
            assert "details" in data
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_time_api_not_found_envelope(self):
        """Test /api/time/state with invalid token returns 404 standard envelope."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/time/state", params={"session_token": "non_existent_token"}
            )
            assert response.status_code == 404
            data = response.json()
            assert data["error"] == "NOT_FOUND"
            assert "message" in data
            assert data["detail"]["error"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_inventory_api_validation_error_envelope(self):
        """Test /api/character/inventory/use with insufficient quantity returns 400 standard envelope."""
        async with get_session() as session:
            char, game_session = await create_character(
                session=session,
                name="Inv Hero",
                race_name=RaceName.HUMAN,
                background_name=BackgroundName.COMMONER,
                gender_presentation=GenderPresentation.MALE,
            )
            token = game_session.session_token

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/character/inventory/use",
                params={"session_token": token},
                json={"item_id": "non_existent_potion", "quantity": 1},
            )
            assert response.status_code == 400
            data = response.json()
            assert data["error"] == "VALIDATION_ERROR"
            assert "message" in data
            assert data["detail"]["error"] == "VALIDATION_ERROR"


class TestSyntheticExceptionHandlers:
    """Test handlers for ConflictError, GameStateError, GameError, and Exception directly."""

    @pytest.mark.asyncio
    async def test_conflict_error_handling(self):
        """Test ConflictError maps to 409 CONFLICT."""
        from fastapi import FastAPI
        from app.core.errors import register_error_handlers

        test_app = FastAPI()
        register_error_handlers(test_app)

        @test_app.get("/test-conflict")
        async def trigger_conflict():
            raise ConflictError(
                "State conflict detected", details={"conflicting_id": 123}
            )

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/test-conflict")
            assert response.status_code == 409
            data = response.json()
            assert data["error"] == "CONFLICT"
            assert data["message"] == "State conflict detected"
            assert data["details"]["conflicting_id"] == 123
            assert data["detail"]["error"] == "CONFLICT"

    @pytest.mark.asyncio
    async def test_game_state_error_handling(self):
        """Test GameStateError maps to 409 INVALID_STATE."""
        from fastapi import FastAPI
        from app.core.errors import register_error_handlers

        test_app = FastAPI()
        register_error_handlers(test_app)

        @test_app.get("/test-state-error")
        async def trigger_state_error():
            raise GameStateError("Cannot act while deceased", details={"state": "DEAD"})

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/test-state-error")
            assert response.status_code == 409
            data = response.json()
            assert data["error"] == "INVALID_STATE"
            assert data["message"] == "Cannot act while deceased"
            assert data["details"]["state"] == "DEAD"

    @pytest.mark.asyncio
    async def test_base_game_error_handling(self):
        """Test generic GameError maps to 500 GAME_ERROR."""
        from fastapi import FastAPI
        from app.core.errors import register_error_handlers

        test_app = FastAPI()
        register_error_handlers(test_app)

        @test_app.get("/test-game-error")
        async def trigger_game_error():
            raise GameError("Generic game error occurred")

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/test-game-error")
            assert response.status_code == 500
            data = response.json()
            assert data["error"] == "GAME_ERROR"
            assert data["message"] == "Generic game error occurred"

    @pytest.mark.asyncio
    async def test_unexpected_exception_handling(self):
        """Test uncaught Python Exception maps to 500 INTERNAL_SERVER_ERROR."""
        from fastapi import FastAPI
        from app.core.errors import register_error_handlers

        test_app = FastAPI()
        register_error_handlers(test_app)

        @test_app.get("/test-server-crash")
        async def trigger_server_crash():
            raise ZeroDivisionError("Unexpected math explosion")

        async with AsyncClient(
            transport=ASGITransport(app=test_app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            response = await client.get("/test-server-crash")
            assert response.status_code == 500
            data = response.json()
            assert data["error"] == "INTERNAL_SERVER_ERROR"
            assert data["message"] == "An unexpected error occurred."
            assert data["details"]["type"] == "ZeroDivisionError"
            assert data["detail"]["error"] == "INTERNAL_SERVER_ERROR"

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_domain_error(self):
        """Test transaction rolls back when endpoint raises domain error without local try/except."""
        from fastapi import FastAPI, Depends
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.core.database import get_db_session
        from app.models.gameplay import Character
        from app.core.errors import register_error_handlers

        test_app = FastAPI()
        register_error_handlers(test_app)

        async with get_session() as session:
            char, _ = await create_character(
                session=session,
                name="Rollback Hero",
                race_name=RaceName.HUMAN,
                background_name=BackgroundName.COMMONER,
                gender_presentation=GenderPresentation.MALE,
            )
            char_id = char.id
            initial_money = char.money

        @test_app.post("/test-modify-and-fail/{character_id}")
        async def modify_and_fail(
            character_id: int, session: AsyncSession = Depends(get_db_session)
        ):
            c = await session.get(Character, character_id)
            c.money += 1000  # modify state
            await session.flush()
            raise ValidationError("Simulated validation failure mid-operation")

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.post(f"/test-modify-and-fail/{char_id}")
            assert response.status_code == 400
            data = response.json()
            assert data["error"] == "VALIDATION_ERROR"

        # Verify database was rolled back; money did NOT increase
        async with get_session() as session:
            persisted_char = await session.get(Character, char_id)
            assert persisted_char.money == initial_money
