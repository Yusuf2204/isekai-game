"""Inventory and treatment schemas."""

from pydantic import BaseModel, Field
from typing import Optional, Literal


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
    item_name: str = Field(..., description="Item display name")
    quantity: int = Field(1, ge=1, description="Quantity to use")


class UseItemResponse(BaseModel):
    """Response schema for using an item."""

    success: bool
    message: str
    item_consumed: dict


class TreatmentRequest(BaseModel):
    """Request schema for treating a condition."""

    treatment_id: str = Field(..., description="Treatment identifier (e.g., bandage, medicine)")


class TreatmentResponse(BaseModel):
    """Response schema for treating a condition."""

    success: bool
    removed: bool
    old_severity: int
    new_severity: int
    treatment_used: str
    description: str
    item_consumed: dict


class AvailableTreatmentItem(BaseModel):
    """Schema for an available treatment item."""

    treatment_id: str
    name: str
    description: str
    severity_reduction: int
    in_inventory: bool


class AvailableTreatmentsResponse(BaseModel):
    """Response schema for available treatments for a condition."""

    condition_id: str
    available_treatments: list[AvailableTreatmentItem]