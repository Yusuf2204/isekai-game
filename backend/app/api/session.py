"""Game session summary and history API router."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.session import (
    EndSessionRequest,
    SessionHistoryItemSchema,
    SessionHistoryResponse,
    SessionSummaryResponse,
)
from app.services.game.session import (
    end_session,
    get_session_summary,
    list_session_history,
)

router = APIRouter(prefix="/session", tags=["session"])


@router.get(
    "/summary",
    response_model=SessionSummaryResponse,
    summary="Retrieve complete session summary across generations",
)
async def get_summary_endpoint(
    session_token: str = Query(..., description="Active session token"),
    session: AsyncSession = Depends(get_db_session),
) -> SessionSummaryResponse:
    """
    Retrieve authoritative session summary per SPEC.md §10.

    Presents total generations, characters created, total time lived,
    death records, legacies passed, skills developed, and earned achievements.
    """
    summary_data = await get_session_summary(session, session_token)
    return SessionSummaryResponse.model_validate(summary_data)


@router.post(
    "/end",
    response_model=SessionSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Conclude session and generate final session summary",
)
async def end_session_endpoint(
    request: EndSessionRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SessionSummaryResponse:
    """
    Formally conclude a game session.

    Retires any active living character and produces the final immutable session summary.
    """
    summary_data = await end_session(session, request.session_token)
    return SessionSummaryResponse.model_validate(summary_data)


@router.get(
    "/history",
    response_model=SessionHistoryResponse,
    summary="List past game sessions archive",
)
async def list_history_endpoint(
    limit: int = Query(default=20, ge=1, le=100, description="Max sessions to return"),
    session: AsyncSession = Depends(get_db_session),
) -> SessionHistoryResponse:
    """List historical player sessions."""
    sessions = await list_session_history(session, limit=limit)
    return SessionHistoryResponse(
        total_sessions=len(sessions),
        sessions=[SessionHistoryItemSchema.model_validate(s) for s in sessions],
    )
