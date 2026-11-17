"""Condition API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.core.exceptions import GameError, NotFoundError, ResourceError, ValidationError
from app.models.gameplay import Character
from app.schemas.conditions import (
    AllConditionsResponse,
    AllTreatmentsResponse,
    AvailableTreatmentsResponse,
    ConditionDefinitionResponse,
    ConditionListResponse,
    ConditionResponse,
    TreatmentDefinitionResponse,
    TreatmentRequest,
    TreatmentResponse,
)
from app.services.character.conditions import (
    get_all_conditions,
    get_character_conditions,
    treat_condition,
)
from app.services.character.creation import get_or_create_session
from app.services.character.inventory import (
    get_all_treatments,
    get_available_treatments_for_condition,
)

router = APIRouter(tags=["conditions"], prefix="/conditions")


async def _get_character_with_relations(
    session: AsyncSession, game_session_id: int, generation: int
) -> Character | None:
    """Get character with attributes, skills, and inventory eagerly loaded."""
    result = await session.execute(
        select(Character)
        .where(
            Character.session_id == game_session_id, Character.generation == generation
        )
        .options(
            selectinload(Character.attributes),
            selectinload(Character.skills),
            selectinload(Character.inventory),
        )
    )
    return result.scalar_one_or_none()


@router.get("/", response_model=ConditionListResponse)
async def get_conditions_endpoint(
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> ConditionListResponse:
    """
    Get all conditions affecting the current character.
    """
    try:
        # Get session
        game_session = await get_or_create_session(session, session_token)

        # Get current character
        character = await _get_character_with_relations(
            session, game_session.id, game_session.current_generation
        )
        if character is None:
            raise NotFoundError("Character", "current generation")

        # Get conditions
        conditions = await get_character_conditions(character)

        return ConditionListResponse(
            conditions=[ConditionResponse(**c) for c in conditions]
        )

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


@router.get("/definitions", response_model=AllConditionsResponse)
async def get_all_conditions_endpoint() -> AllConditionsResponse:
    """
    Get all available condition definitions (for reference).
    """
    conditions = await get_all_conditions()

    defs = []
    for cond_id, cond in conditions.items():
        defs.append(
            ConditionDefinitionResponse(
                id=cond_id,
                name=cond["name"],
                description=cond["description"],
                base_severity=cond["base_severity"],
                max_duration=cond["max_duration"],
                health_per_period=cond["health_per_period"],
                stamina_penalty=cond["stamina_penalty"],
                attribute_penalties=cond["attribute_penalties"],
            )
        )

    return AllConditionsResponse(conditions=defs)


@router.get("/treatments", response_model=AllTreatmentsResponse)
async def get_all_treatments_endpoint() -> AllTreatmentsResponse:
    """
    Get all available treatment definitions (for reference).
    """
    treatments_dict = await get_all_treatments()

    treatments = []
    for treat_id, treat in treatments_dict.items():
        treatments.append(
            TreatmentDefinitionResponse(
                id=treat_id,
                name=treat["name"],
                treats=treat["treats"],
                severity_reduction=treat["severity_reduction"],
                description=treat["description"],
            )
        )

    return AllTreatmentsResponse(treatments=treatments)


@router.get("/{condition_id}/treatments", response_model=AvailableTreatmentsResponse)
async def get_available_treatments_endpoint(
    condition_id: str,
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> AvailableTreatmentsResponse:
    """
    Get available treatments for a specific condition that are in inventory.
    """
    try:
        # Get session
        game_session = await get_or_create_session(session, session_token)

        # Get current character
        character = await _get_character_with_relations(
            session, game_session.id, game_session.current_generation
        )
        if character is None:
            raise NotFoundError("Character", "current generation")

        # Check if condition exists
        if not character.conditions or condition_id not in character.conditions:
            raise NotFoundError("Condition", condition_id)

        # Get available treatments
        available = await get_available_treatments_for_condition(
            session, character, condition_id
        )

        return AvailableTreatmentsResponse(
            condition_id=condition_id,
            available_treatments=available,
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.code, "message": e.message, "details": e.details},
        )
    except (ValidationError, ResourceError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": e.code, "message": e.message, "details": e.details},
        )
    except GameError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": e.code, "message": e.message, "details": e.details},
        )


@router.post("/treat", response_model=TreatmentResponse)
async def treat_condition_endpoint(
    request: TreatmentRequest,
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> TreatmentResponse:
    """
    Treat a condition using a treatment item.
    """
    try:
        # Get session
        game_session = await get_or_create_session(session, session_token)

        # Get current character
        character = await _get_character_with_relations(
            session, game_session.id, game_session.current_generation
        )
        if character is None:
            raise NotFoundError("Character", "current generation")

        # Treat condition
        result = await treat_condition(
            session, character, request.condition_id, request.treatment_id
        )

        return TreatmentResponse(**result)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.code, "message": e.message, "details": e.details},
        )
    except (ValidationError, ResourceError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": e.code, "message": e.message, "details": e.details},
        )
    except GameError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": e.code, "message": e.message, "details": e.details},
        )
