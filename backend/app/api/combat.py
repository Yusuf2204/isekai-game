"""Combat API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.exceptions import NotFoundError
from app.models.gameplay import Character, GameSession
from app.schemas.combat import (
    CombatActionRequest,
    CombatActionResponse,
    CombatStartRequest,
    CombatStateResponse,
)
from app.services.combat.service import (
    execute_combat_turn,
    get_combat_state,
    start_combat,
)

router = APIRouter(tags=["combat"], prefix="/combat")


async def _resolve_character_from_session_token(
    session: AsyncSession, session_token: str
) -> Character:
    """Resolve current active character from game session token."""
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


@router.post("/start", response_model=CombatStateResponse)
async def start_combat_endpoint(
    request: CombatStartRequest,
    session: AsyncSession = Depends(get_db_session),
) -> CombatStateResponse:
    """Initiate a combat encounter or resume existing active combat."""
    character = await _resolve_character_from_session_token(
        session, request.session_token
    )
    result = await start_combat(
        session=session,
        character_id=character.id,
        enemy_type=request.enemy_type,
        rng_seed=request.rng_seed,
    )
    return CombatStateResponse(**result)


@router.get("/state", response_model=CombatStateResponse)
async def get_combat_state_endpoint(
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> CombatStateResponse:
    """Inspect current active combat status for a character."""
    character = await _resolve_character_from_session_token(session, session_token)
    result = await get_combat_state(session=session, character_id=character.id)
    return CombatStateResponse(**result)


@router.post("/action", response_model=CombatActionResponse)
async def execute_combat_action_endpoint(
    request: CombatActionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> CombatActionResponse:
    """Execute a combat turn action (attack, defend, use_skill, use_item, flee)."""
    character = await _resolve_character_from_session_token(
        session, request.session_token
    )
    result = await execute_combat_turn(
        session=session,
        character_id=character.id,
        action=request.action,
        skill_name=request.skill_name,
        item_name=request.item_name,
        rng_seed=request.rng_seed,
    )
    return CombatActionResponse(**result)
