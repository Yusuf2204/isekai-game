"""Session summary and session history schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.reincarnation import CharacterLegacyResponse, LifeRecordResponse


class SessionSummaryCharacterSchema(BaseModel):
    """Snapshot of a character created within a session."""

    model_config = ConfigDict(from_attributes=True)

    character_id: int
    generation: int
    name: str
    race_name: str
    background_name: str
    gender_presentation: str
    is_alive: bool
    age: int
    level: int
    cause_of_death: Optional[str] = None
    death_description: Optional[str] = None


class SessionSummaryResponse(BaseModel):
    """Authoritative session summary per SPEC.md §10."""

    model_config = ConfigDict(from_attributes=True)

    session_id: int
    session_token: str
    seed: int
    is_active: bool
    total_generations: int
    total_deaths: int
    total_time_lived: int  # in days
    created_at: datetime
    ended_at: Optional[datetime] = None
    characters_created: list[SessionSummaryCharacterSchema]
    death_records: list[LifeRecordResponse]
    legacies_passed: list[CharacterLegacyResponse]
    skills_developed: dict[str, int]
    important_decisions: list[dict[str, Any]]
    achievements: list[str]


class EndSessionRequest(BaseModel):
    """Request payload to officially conclude a game session."""

    session_token: str = Field(..., description="Active session token to end")


class SessionHistoryItemSchema(BaseModel):
    """High-level summary of a past game session."""

    model_config = ConfigDict(from_attributes=True)

    session_id: int
    session_token: str
    seed: int
    is_active: bool
    total_generations: int
    total_deaths: int
    total_time_lived: int
    created_at: datetime
    ended_at: Optional[datetime] = None


class SessionHistoryResponse(BaseModel):
    """Historical archive of player game sessions."""

    total_sessions: int
    sessions: list[SessionHistoryItemSchema]
