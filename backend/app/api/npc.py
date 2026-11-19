"""NPC interaction and relationship API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.exceptions import NotFoundError
from app.models.gameplay import Character, GameSession
from app.models.world import Location
from app.schemas.npc import (
    AllRelationshipsResponse,
    NPCDetailResponse,
    NPCGiftRequest,
    NPCGiftResponse,
    NPCListResponse,
    NPCRelationshipSummary,
    NPCSummarySchema,
    NPCTalkRequest,
    NPCTalkResponse,
)
from app.services.npc.service import (
    get_all_character_relationships,
    get_npc_profile,
    get_npcs_by_location,
    give_gift_to_npc,
    talk_to_npc,
)

router = APIRouter(tags=["npc"], prefix="/npc")


async def _resolve_character(
    session: AsyncSession, session_token: Optional[str]
) -> Optional[Character]:
    """Optionally resolve current character from session token."""
    if not session_token:
        return None

    res = await session.execute(
        select(GameSession).where(GameSession.session_token == session_token)
    )
    game_session = res.scalar_one_or_none()
    if not game_session:
        raise NotFoundError("GameSession", session_token)

    char_res = await session.execute(
        select(Character).where(
            Character.session_id == game_session.id,
            Character.generation == game_session.current_generation,
        )
    )
    character = char_res.scalar_one_or_none()
    if not character:
        raise NotFoundError("Character", "current generation")

    return character


@router.get("/relationships", response_model=AllRelationshipsResponse)
async def get_relationships_endpoint(
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> AllRelationshipsResponse:
    """Retrieve all active NPC relationships for the current player character."""
    character = await _resolve_character(session, session_token)
    assert character is not None

    relationships = await get_all_character_relationships(session, character.id)
    return AllRelationshipsResponse(
        character_id=character.id,
        relationships=[NPCRelationshipSummary(**rel) for rel in relationships],
    )


@router.get("/location/{location_id}", response_model=NPCListResponse)
async def get_npcs_by_location_endpoint(
    location_id: int,
    session_token: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session),
) -> NPCListResponse:
    """List all NPCs present in a given location."""
    loc = await session.get(Location, location_id)
    if loc is None:
        raise NotFoundError("Location", location_id)

    char_id = None
    if session_token:
        character = await _resolve_character(session, session_token)
        if character:
            char_id = character.id

    npcs_data = await get_npcs_by_location(
        session=session, location_id=location_id, character_id=char_id
    )

    return NPCListResponse(
        location_id=location_id,
        location_name=loc.name,
        npcs=[NPCSummarySchema(**npc) for npc in npcs_data],
    )


@router.get("/{npc_id}", response_model=NPCDetailResponse)
async def get_npc_detail_endpoint(
    npc_id: int,
    session_token: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session),
) -> NPCDetailResponse:
    """Get the full profile and relationship status of an NPC."""
    char_id = None
    if session_token:
        character = await _resolve_character(session, session_token)
        if character:
            char_id = character.id

    profile = await get_npc_profile(
        session=session, npc_id=npc_id, character_id=char_id
    )
    return NPCDetailResponse(**profile)


@router.post("/{npc_id}/talk", response_model=NPCTalkResponse)
async def talk_to_npc_endpoint(
    npc_id: int,
    request: NPCTalkRequest,
    session: AsyncSession = Depends(get_db_session),
) -> NPCTalkResponse:
    """Engage in dialogue with an NPC, adjusting relationship, trust, and memory flags."""
    character = await _resolve_character(session, request.session_token)
    assert character is not None

    result = await talk_to_npc(
        session=session,
        character_id=character.id,
        npc_id=npc_id,
        topic=request.topic,
    )
    return NPCTalkResponse(**result)


@router.post("/{npc_id}/gift", response_model=NPCGiftResponse)
async def gift_to_npc_endpoint(
    npc_id: int,
    request: NPCGiftRequest,
    session: AsyncSession = Depends(get_db_session),
) -> NPCGiftResponse:
    """Give a monetary or item gift to an NPC to improve relationship and trust."""
    character = await _resolve_character(session, request.session_token)
    assert character is not None

    result = await give_gift_to_npc(
        session=session,
        character_id=character.id,
        npc_id=npc_id,
        item_name=request.item_name,
        money=request.money,
    )
    return NPCGiftResponse(**result)
