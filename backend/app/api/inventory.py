"""Inventory API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.core.exceptions import GameError, NotFoundError, ValidationError, ResourceError
from app.models.gameplay import Character, GameplayState
from app.schemas.inventory import (
    InventoryResponse,
    InventoryItemResponse,
    UseItemRequest,
    UseItemResponse,
    TreatmentRequest,
    TreatmentResponse,
    AvailableTreatmentsResponse,
)
from app.services.character.creation import get_or_create_session
from app.services.character.inventory import (
    get_inventory,
    has_item,
    consume_item_by_name,
    get_available_treatments_for_condition,
    get_treatment_definition,
    get_all_treatments,
)
from app.services.character.conditions import get_character_conditions

router = APIRouter(tags=["inventory"], prefix="/character")


async def _get_character_with_inventory(
    session: AsyncSession, game_session_id: int, generation: int
) -> Character | None:
    """Get character with inventory eagerly loaded."""
    result = await session.execute(
        select(Character)
        .where(
            Character.session_id == game_session_id, Character.generation == generation
        )
        .options(selectinload(Character.inventory))
    )
    return result.scalar_one_or_none()


@router.get("/inventory", response_model=InventoryResponse)
async def get_inventory_endpoint(
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> InventoryResponse:
    """
    Get character's full inventory with details.
    """
    try:
        # Get session
        game_session = await get_or_create_session(session, session_token)

        # Get current character with inventory
        character = await _get_character_with_inventory(
            session, game_session.id, game_session.current_generation
        )
        if character is None:
            raise NotFoundError("Character", "current generation")

        # Get inventory
        inventory = await get_inventory(character)

        # Calculate total value
        total_value = sum(item["value"] * item["quantity"] for item in inventory)

        return InventoryResponse(
            inventory=inventory,
            total_items=len(inventory),
            total_value=total_value,
            money=character.money,
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


@router.post("/inventory/use", response_model=UseItemResponse)
async def use_item_endpoint(
    request: UseItemRequest,
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> UseItemResponse:
    """
    Use/consume an item from inventory by name.

    This is for general item consumption (food, potions, etc.).
    For treating conditions, use the /treat endpoint.
    """
    try:
        # Get session
        game_session = await get_or_create_session(session, session_token)

        # Get current character
        character = await _get_character_with_inventory(
            session, game_session.id, game_session.current_generation
        )
        if character is None:
            raise NotFoundError("Character", "current generation")

        # Check if character has the item
        if not await has_item(session, character, request.item_id, request.quantity):
            raise ResourceError(
                f"Insufficient quantity of item",
                details={
                    "item_id": request.item_id,
                    "required": request.quantity,
                },
            )

        # Consume the item
        result = await consume_item_by_name(
            session, character, request.item_name, request.quantity
        )

        await session.commit()

        return UseItemResponse(
            success=True,
            message=f"Used {request.quantity}x {request.item_name}",
            item_consumed=result,
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


@router.get("/conditions", response_model=list[dict])
async def get_conditions_endpoint(
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    """
    Get character's current conditions.
    """
    try:
        # Get session
        game_session = await get_or_create_session(session, session_token)

        # Get current character
        character = await _get_character_with_inventory(
            session, game_session.id, game_session.current_generation
        )
        if character is None:
            raise NotFoundError("Character", "current generation")

        # Get conditions
        conditions = await get_character_conditions(character)

        return conditions

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


@router.get("/treatments", response_model=dict)
async def get_treatments_endpoint(
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Get all available treatment definitions.
    """
    try:
        # Get session
        game_session = await get_or_create_session(session, session_token)

        # Get current character (just to validate session)
        character = await _get_character_with_inventory(
            session, game_session.id, game_session.current_generation
        )
        if character is None:
            raise NotFoundError("Character", "current generation")

        # Get all treatments
        treatments = await get_all_treatments()

        return {"treatments": treatments}

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


@router.get("/conditions/{condition_id}/treatments", response_model=AvailableTreatmentsResponse)
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
        character = await _get_character_with_inventory(
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
    except GameError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": e.code, "message": e.message, "details": e.details},
        )


@router.post("/conditions/{condition_id}/treat", response_model=TreatmentResponse)
async def treat_condition_endpoint(
    condition_id: str,
    request: TreatmentRequest,
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> TreatmentResponse:
    """
    Treat a condition using a treatment item from inventory.

    This atomically consumes the treatment item and applies the treatment effect.
    """
    try:
        # Get session
        game_session = await get_or_create_session(session, session_token)

        # Get current character
        character = await _get_character_with_inventory(
            session, game_session.id, game_session.current_generation
        )
        if character is None:
            raise NotFoundError("Character", "current generation")

        # Treat condition
        from app.services.character.inventory import treat_condition_with_item

        result = await treat_condition_with_item(
            session=session,
            character=character,
            condition_id=condition_id,
            treatment_id=request.treatment_id,
        )

        await session.commit()

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