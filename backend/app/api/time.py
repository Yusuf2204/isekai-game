"""Time system API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.exceptions import GameError, NotFoundError, ValidationError
from app.models.gameplay import Character, GameplayState
from app.schemas.time import (
    TimeStateResponse,
    AdvanceTimeRequest,
    AdvanceTimeResponse,
    TimePeriodsResponse,
    TimePeriodInfo,
)
from app.services.game import (
    get_current_time_state,
    advance_time,
    get_all_time_periods,
)
from app.services.character.creation import get_or_create_session

router = APIRouter(tags=["time"], prefix="/time")


@router.get("/state", response_model=TimeStateResponse)
async def get_time_state_endpoint(
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> TimeStateResponse:
    """
    Get the current in-game time state.

    Returns the current day, time of day, and description.
    """
    try:
        # Get session
        game_session = await get_or_create_session(session, session_token)

        # Get current character
        from sqlalchemy import select

        result = await session.execute(
            select(Character).where(
                Character.session_id == game_session.id,
                Character.generation == game_session.current_generation,
            )
        )
        character = result.scalar_one_or_none()
        if character is None:
            raise NotFoundError("Character", "current generation")

        # Get gameplay state
        result = await session.execute(
            select(GameplayState).where(GameplayState.session_id == game_session.id)
        )
        gameplay_state = result.scalar_one_or_none()
        if gameplay_state is None:
            raise NotFoundError("GameplayState", str(game_session.id))

        time_state = await get_current_time_state(gameplay_state)

        return TimeStateResponse(**time_state)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.code, "message": e.message, "details": e.details},
        )
    except GameError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": e.code, "message": e.message, "details": e.details},
        )


@router.post("/advance", response_model=AdvanceTimeResponse)
async def advance_time_endpoint(
    request: AdvanceTimeRequest,
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> AdvanceTimeResponse:
    """
    Advance in-game time by the specified number of periods.

    Each period advances: MORNING -> AFTERNOON -> EVENING -> NIGHT -> MORNING (next day)
    """
    try:
        # Get session
        game_session = await get_or_create_session(session, session_token)

        # Get current character
        from sqlalchemy import select

        result = await session.execute(
            select(Character).where(
                Character.session_id == game_session.id,
                Character.generation == game_session.current_generation,
            )
        )
        character = result.scalar_one_or_none()
        if character is None:
            raise NotFoundError("Character", "current generation")

        # Get gameplay state
        result = await session.execute(
            select(GameplayState).where(GameplayState.session_id == game_session.id)
        )
        gameplay_state = result.scalar_one_or_none()
        if gameplay_state is None:
            raise NotFoundError("GameplayState", str(game_session.id))

        # Advance time
        advance_result = await advance_time(
            session=session,
            gameplay_state=gameplay_state,
            periods=request.periods,
        )

        await session.commit()

        return AdvanceTimeResponse(**advance_result)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.code, "message": e.message, "details": e.details},
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": e.code, "message": e.message, "details": e.details},
        )
    except GameError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": e.code, "message": e.message, "details": e.details},
        )


@router.get("/periods", response_model=TimePeriodsResponse)
async def get_time_periods_endpoint() -> TimePeriodsResponse:
    """
    Get information about all time periods.

    Returns available activities and NPC availability for each period.
    """
    periods_data = await get_all_time_periods()

    periods = [TimePeriodInfo(**p) for p in periods_data]

    return TimePeriodsResponse(
        periods=periods,
        current_period="morning",  # Default, actual state requires session
    )
