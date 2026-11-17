"""Time system API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.exceptions import NotFoundError
from app.models.gameplay import Character, GameplayState
from app.schemas.time import (
    AdvanceTimeRequest,
    AdvanceTimeResponse,
    TimePeriodInfo,
    TimePeriodsResponse,
    TimeStateResponse,
)
from app.services.character.creation import get_or_create_session
from app.services.game import (
    advance_time,
    get_all_time_periods,
    get_current_time_state,
)

router = APIRouter(tags=["time"], prefix="/time")


@router.get("/state", response_model=TimeStateResponse)
async def get_time_state_endpoint(
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> TimeStateResponse:
    """Get the current in-game time state.

    Returns the current day, time of day, and description.
    """
    game_session = await get_or_create_session(session, session_token)

    result = await session.execute(
        select(Character).where(
            Character.session_id == game_session.id,
            Character.generation == game_session.current_generation,
        )
    )
    character = result.scalar_one_or_none()
    if character is None:
        raise NotFoundError("Character", "current generation")

    result = await session.execute(
        select(GameplayState).where(GameplayState.session_id == game_session.id)
    )
    gameplay_state = result.scalar_one_or_none()
    if gameplay_state is None:
        raise NotFoundError("GameplayState", str(game_session.id))

    time_state = await get_current_time_state(gameplay_state)

    return TimeStateResponse(**time_state)


@router.post("/advance", response_model=AdvanceTimeResponse)
async def advance_time_endpoint(
    request: AdvanceTimeRequest,
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> AdvanceTimeResponse:
    """Advance in-game time by the specified number of periods.

    Each period advances: MORNING -> AFTERNOON -> EVENING -> NIGHT -> MORNING (next day)
    """
    game_session = await get_or_create_session(session, session_token)

    result = await session.execute(
        select(Character).where(
            Character.session_id == game_session.id,
            Character.generation == game_session.current_generation,
        )
    )
    character = result.scalar_one_or_none()
    if character is None:
        raise NotFoundError("Character", "current generation")

    result = await session.execute(
        select(GameplayState).where(GameplayState.session_id == game_session.id)
    )
    gameplay_state = result.scalar_one_or_none()
    if gameplay_state is None:
        raise NotFoundError("GameplayState", str(game_session.id))

    advance_result = await advance_time(
        session=session,
        gameplay_state=gameplay_state,
        periods=request.periods,
    )

    return AdvanceTimeResponse(**advance_result)


@router.get("/periods", response_model=TimePeriodsResponse)
async def get_time_periods_endpoint(
    session_token: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> TimePeriodsResponse:
    """Get information about all time periods.

    Returns available activities and NPC availability for each period.

    If session token is provided, returns the real current_period from gameplay state.
    Otherwise, returns null for current_period.
    """
    periods_data = await get_all_time_periods()
    periods = [TimePeriodInfo(**p) for p in periods_data]

    current_period: str | None = None

    if session_token:
        game_session = await get_or_create_session(session, session_token)

        result = await session.execute(
            select(Character).where(
                Character.session_id == game_session.id,
                Character.generation == game_session.current_generation,
            )
        )
        character = result.scalar_one_or_none()
        if character is None:
            raise NotFoundError("Character", "current generation")

        result = await session.execute(
            select(GameplayState).where(GameplayState.session_id == game_session.id)
        )
        gameplay_state = result.scalar_one_or_none()
        if gameplay_state is None:
            raise NotFoundError("GameplayState", str(game_session.id))

        current_period = gameplay_state.current_time_of_day.value

    return TimePeriodsResponse(
        periods=periods,
        current_period=current_period,
    )
