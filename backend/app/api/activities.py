"""Activity API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.core.exceptions import NotFoundError
from app.models.gameplay import Character, GameplayState
from app.schemas.activities import (
    ActivityListResponse,
    ExploreRequest,
    ExploreResponse,
    RestRequest,
    RestResponse,
    WorkRequest,
    WorkResponse,
)
from app.services.character.creation import get_or_create_session
from app.services.game import (
    get_available_activities,
    perform_explore,
    perform_rest,
    perform_work,
)

router = APIRouter(tags=["activities"], prefix="/activities")


async def _get_character_with_relations(
    session: AsyncSession, game_session_id: int, generation: int
) -> Character | None:
    """Get character with attributes and skills eagerly loaded."""
    result = await session.execute(
        select(Character)
        .where(
            Character.session_id == game_session_id, Character.generation == generation
        )
        .options(selectinload(Character.attributes), selectinload(Character.skills))
    )
    return result.scalar_one_or_none()


@router.get("/available", response_model=ActivityListResponse)
async def get_available_activities_endpoint(
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> ActivityListResponse:
    """Get available activities based on current location and time."""
    game_session = await get_or_create_session(session, session_token)

    character = await _get_character_with_relations(
        session, game_session.id, game_session.current_generation
    )
    if character is None:
        raise NotFoundError("Character", "current generation")

    result = await session.execute(
        select(GameplayState).where(GameplayState.session_id == game_session.id)
    )
    gameplay_state = result.scalar_one_or_none()
    if gameplay_state is None:
        raise NotFoundError("GameplayState", str(game_session.id))

    activities = await get_available_activities(session, character, gameplay_state)
    return ActivityListResponse(**activities)


@router.post("/explore", response_model=ExploreResponse)
async def explore_endpoint(
    request: ExploreRequest,
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> ExploreResponse:
    """Explore the current location or a specified location.

    Consumes 1 time period. May discover items, money, or gain experience.
    """
    game_session = await get_or_create_session(session, session_token)

    character = await _get_character_with_relations(
        session, game_session.id, game_session.current_generation
    )
    if character is None:
        raise NotFoundError("Character", "current generation")

    result = await session.execute(
        select(GameplayState).where(GameplayState.session_id == game_session.id)
    )
    gameplay_state = result.scalar_one_or_none()
    if gameplay_state is None:
        raise NotFoundError("GameplayState", str(game_session.id))

    explore_result = await perform_explore(
        session=session,
        character=character,
        gameplay_state=gameplay_state,
        location_id=request.location_id,
    )
    return ExploreResponse(**explore_result)


@router.post("/rest", response_model=RestResponse)
async def rest_endpoint(
    request: RestRequest,
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> RestResponse:
    """Rest to recover health.

    Short rest: 1 period, recovers ~15 health.
    Long rest: 2 periods, recovers ~30 health but may be interrupted at night.
    """
    game_session = await get_or_create_session(session, session_token)

    character = await _get_character_with_relations(
        session, game_session.id, game_session.current_generation
    )
    if character is None:
        raise NotFoundError("Character", "current generation")

    result = await session.execute(
        select(GameplayState).where(GameplayState.session_id == game_session.id)
    )
    gameplay_state = result.scalar_one_or_none()
    if gameplay_state is None:
        raise NotFoundError("GameplayState", str(game_session.id))

    rest_result = await perform_rest(
        session=session,
        character=character,
        gameplay_state=gameplay_state,
        duration=request.duration,
    )
    return RestResponse(**rest_result)


@router.post("/work", response_model=WorkResponse)
async def work_endpoint(
    request: WorkRequest,
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> WorkResponse:
    """Work at the current location to earn money and skill experience.

    Available work types depend on location. Consumes 1 time period.
    """
    game_session = await get_or_create_session(session, session_token)

    character = await _get_character_with_relations(
        session, game_session.id, game_session.current_generation
    )
    if character is None:
        raise NotFoundError("Character", "current generation")

    result = await session.execute(
        select(GameplayState).where(GameplayState.session_id == game_session.id)
    )
    gameplay_state = result.scalar_one_or_none()
    if gameplay_state is None:
        raise NotFoundError("GameplayState", str(game_session.id))

    work_result = await perform_work(
        session=session,
        character=character,
        gameplay_state=gameplay_state,
        work_type=request.work_type,
    )
    return WorkResponse(**work_result)
