"""Inventory API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.core.exceptions import NotFoundError
from app.models.gameplay import Character
from app.schemas.inventory import (
    InventoryResponse,
    UseItemRequest,
    UseItemResponse,
)
from app.services.character.creation import get_or_create_session
from app.services.character.inventory import (
    consume_item,
    get_inventory,
)

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
    """Get character's full inventory with details."""
    game_session = await get_or_create_session(session, session_token)

    character = await _get_character_with_inventory(
        session, game_session.id, game_session.current_generation
    )
    if character is None:
        raise NotFoundError("Character", "current generation")

    inventory = await get_inventory(character)
    total_value = sum(item["value"] * item["quantity"] for item in inventory)

    return InventoryResponse(
        inventory=inventory,
        total_items=len(inventory),
        total_value=total_value,
        money=character.money,
    )


@router.post("/inventory/use", response_model=UseItemResponse)
async def use_item_endpoint(
    request: UseItemRequest,
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> UseItemResponse:
    """Use/consume an item from inventory by item_id.

    This is for general item consumption (food, potions, etc.).
    For treating conditions, use the /conditions/treat endpoint.
    """
    game_session = await get_or_create_session(session, session_token)

    character = await _get_character_with_inventory(
        session, game_session.id, game_session.current_generation
    )
    if character is None:
        raise NotFoundError("Character", "current generation")

    result = await consume_item(session, character, request.item_id, request.quantity)

    item_name = result["name"]

    return UseItemResponse(
        success=True,
        message=f"Used {request.quantity}x {item_name}",
        item_consumed=result,
    )
