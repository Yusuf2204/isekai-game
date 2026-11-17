"""Inventory schemas."""

from pydantic import BaseModel, Field

# Re-exported for backward compatibility
from app.schemas.conditions import (  # noqa: F401
    AvailableTreatmentItem,
    AvailableTreatmentsResponse,
    TreatmentRequest,
    TreatmentResponse,
)


class InventoryItemResponse(BaseModel):
    """Response schema for an inventory item."""

    id: int
    item_id: str
    name: str
    description: str
    quantity: int
    item_type: str
    value: int
    is_equipped: bool
    properties: dict = {}


class InventoryResponse(BaseModel):
    """Response schema for character inventory."""

    inventory: list[InventoryItemResponse]
    total_items: int
    total_value: int
    money: int


class UseItemRequest(BaseModel):
    """Request schema for using an item."""

    item_id: str = Field(..., description="Item identifier")
    item_name: str | None = Field(None, description="Optional item display name")
    quantity: int = Field(1, ge=1, description="Quantity to use")


class UseItemResponse(BaseModel):
    """Response schema for using an item."""

    success: bool
    message: str
    item_consumed: dict
