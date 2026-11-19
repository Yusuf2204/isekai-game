"""Pydantic schemas for the Event System API."""

from typing import Any, Optional
from pydantic import BaseModel, Field
from app.models.enums import EventCategory


class EventChoiceOptionSchema(BaseModel):
    """Option presented to the player during an active event."""

    id: str = Field(..., description="Unique choice identifier within the event")
    label: str = Field(..., description="Action button text")
    description: str = Field(
        ..., description="Detailed description of what this choice entails"
    )
    requires_stat: Optional[str] = Field(
        None, description="Primary attribute tested by this choice, if any"
    )


class EventDisplaySchema(BaseModel):
    """Client-facing active event presentation."""

    id: str = Field(..., description="Event identifier")
    title: str = Field(..., description="Display title")
    category: EventCategory = Field(..., description="Event category")
    description: str = Field(..., description="Atmospheric event narrative")
    choices: list[EventChoiceOptionSchema] = Field(
        ..., description="Available choices for the player"
    )


class ActiveEventResponse(BaseModel):
    """Response containing current active event status."""

    has_active_event: bool = Field(
        ..., description="Whether the character currently has an active event"
    )
    event: Optional[EventDisplaySchema] = Field(
        None, description="Active event details if present"
    )


class EventTriggerRequest(BaseModel):
    """Request to trigger an event."""

    session_token: Optional[str] = Field(None, description="Active game session token")
    event_id: Optional[str] = Field(
        None,
        description="Explicit event ID to trigger (for deterministic testing/story quests)",
    )


class EventChoiceRequest(BaseModel):
    """Request to submit a decision for an active event."""

    session_token: Optional[str] = Field(None, description="Active game session token")
    choice_id: str = Field(..., description="Selected choice identifier")


class StatCheckResultSchema(BaseModel):
    """Outcome of an attribute stat check."""

    attribute: str = Field(..., description="Attribute that was checked")
    difficulty: int = Field(..., description="Target DC value")
    roll: int = Field(..., description="Dice roll + attribute modifier total")
    passed: bool = Field(..., description="Whether the check succeeded")


class EventResolutionResponse(BaseModel):
    """Consequence report returned after resolving an event decision."""

    event_id: str = Field(..., description="ID of resolved event")
    choice_id: str = Field(..., description="Choice selected by player")
    narrative: str = Field(..., description="Outcome story text")
    stat_check: Optional[StatCheckResultSchema] = Field(
        None, description="Stat check details if performed"
    )
    health_change: int = Field(0, description="Net health change applied")
    stamina_change: int = Field(0, description="Net stamina change applied")
    money_change: int = Field(0, description="Net money change applied")
    skill_xp: dict[str, int] = Field(
        default_factory=dict, description="Skill experience gained"
    )
    attribute_xp: dict[str, int] = Field(
        default_factory=dict, description="Attribute experience gained"
    )
    items_added: list[dict[str, Any]] = Field(
        default_factory=list, description="Items added to inventory"
    )
    items_removed: list[dict[str, Any]] = Field(
        default_factory=list, description="Items removed from inventory"
    )
    condition_applied: Optional[str] = Field(
        None, description="Condition inflicted or acquired, if any"
    )
    character_dead: bool = Field(
        False, description="Whether the character died from the event consequences"
    )
    death_cause: Optional[str] = Field(
        None, description="Cause of death if character died"
    )


class EventDefinitionSummarySchema(BaseModel):
    """Summary of an event definition in the catalog."""

    id: str
    title: str
    category: EventCategory
    description: str
    choices_count: int
