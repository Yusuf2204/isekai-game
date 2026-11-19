"""API endpoints for the Event System."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.exceptions import NotFoundError
from app.models.gameplay import Character
from app.schemas.events import (
    ActiveEventResponse,
    EventChoiceRequest,
    EventDefinitionSummarySchema,
    EventResolutionResponse,
    EventTriggerRequest,
)
from app.services.character.creation import get_or_create_session
from app.services.events import (
    get_active_event,
    get_all_event_definitions,
    resolve_event_choice,
    trigger_event,
)

router = APIRouter(tags=["events"], prefix="/events")


async def _resolve_character(
    session: AsyncSession,
    session_token: Optional[str],
) -> Character:
    """Resolve character from session token, matching current generation."""
    game_session = await get_or_create_session(session, session_token)
    result = await session.execute(
        select(Character).where(
            Character.session_id == game_session.id,
            Character.generation == game_session.current_generation,
        )
    )
    character = result.scalar_one_or_none()
    if not character:
        raise NotFoundError("Character", "current generation")
    return character


@router.get("/definitions", response_model=list[EventDefinitionSummarySchema])
async def list_event_definitions() -> list[EventDefinitionSummarySchema]:
    """Get the full catalog of predefined event definitions."""
    return get_all_event_definitions()


@router.get("/active", response_model=ActiveEventResponse)
async def get_active_event_endpoint(
    session_token: Optional[str] = Query(None, description="Active session token"),
    session: AsyncSession = Depends(get_db_session),
) -> ActiveEventResponse:
    """Check if the current character has an active, unresolved event."""
    character = await _resolve_character(session, session_token)
    event = await get_active_event(session, character.id)
    return ActiveEventResponse(
        has_active_event=event is not None,
        event=event,
    )


@router.post("/trigger", response_model=ActiveEventResponse)
async def trigger_event_endpoint(
    request: EventTriggerRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ActiveEventResponse:
    """Trigger a new event for the current character.

    If an event is already active, returns the existing active event.
    """
    character = await _resolve_character(session, request.session_token)
    display_event = await trigger_event(
        session=session,
        character_id=character.id,
        forced_event_id=request.event_id,
    )
    return ActiveEventResponse(
        has_active_event=True,
        event=display_event,
    )


@router.post("/choose", response_model=EventResolutionResponse)
async def resolve_choice_endpoint(
    request: EventChoiceRequest,
    session: AsyncSession = Depends(get_db_session),
) -> EventResolutionResponse:
    """Submit a decision for the character's active event and receive the authoritative consequences."""
    character = await _resolve_character(session, request.session_token)
    return await resolve_event_choice(
        session=session,
        character_id=character.id,
        choice_id=request.choice_id,
    )
