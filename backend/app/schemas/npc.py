"""Pydantic schemas for the NPC interaction and relationship system."""

from typing import Optional
from pydantic import BaseModel, Field


class NPCSummarySchema(BaseModel):
    """Summary of an NPC in a location."""

    id: int
    name: str
    race_name: str
    age: int
    personality: str
    occupation: str
    location_id: int
    location_name: Optional[str] = None
    is_essential: bool = False
    relationship_value: Optional[int] = None
    trust: Optional[int] = None
    available_times: list[str] = Field(default_factory=list)


class NPCDetailResponse(BaseModel):
    """Detailed profile of an NPC and the player's relationship with them."""

    id: int
    name: str
    race_name: str
    age: int
    personality: str
    occupation: str
    location_id: int
    location_name: str
    description: str
    background_story: str
    greeting: str
    farewell: str
    available_times: list[str]
    is_essential: bool
    relationship_value: int = 0
    trust: int = 0
    memory_flags: dict[str, bool] = Field(default_factory=dict)


class NPCListResponse(BaseModel):
    """List of NPCs present at a location."""

    location_id: int
    location_name: str
    npcs: list[NPCSummarySchema]


class NPCTalkRequest(BaseModel):
    """Request to speak with an NPC."""

    session_token: str
    topic: Optional[str] = None


class NPCTalkResponse(BaseModel):
    """Response returned after speaking with an NPC."""

    npc_id: int
    npc_name: str
    greeting: str
    dialogue: str
    farewell: str
    relationship_value: int
    trust: int
    relationship_change: int
    trust_change: int
    memory_flags: dict[str, bool]
    current_period: Optional[str] = None


class NPCGiftRequest(BaseModel):
    """Request to give a gift of money or an item to an NPC."""

    session_token: str
    item_name: Optional[str] = None
    money: int = Field(default=0, ge=0)


class NPCGiftResponse(BaseModel):
    """Response returned after gifting an NPC."""

    npc_id: int
    npc_name: str
    message: str
    gift_accepted: bool
    money_gifted: int
    item_gifted: Optional[str] = None
    relationship_value: int
    trust: int
    relationship_change: int
    trust_change: int
    remaining_money: int
    memory_flags: dict[str, bool]


class NPCRelationshipSummary(BaseModel):
    """Summary of a single relationship with an NPC."""

    npc_id: int
    npc_name: str
    occupation: str
    location_name: str
    relationship_value: int
    trust: int
    relationship_tier: str
    memory_flags: dict[str, bool]


class AllRelationshipsResponse(BaseModel):
    """List of all relationships for the current character."""

    character_id: int
    relationships: list[NPCRelationshipSummary]
