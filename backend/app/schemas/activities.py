"""Activity schemas."""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class ActivityResult(BaseModel):
    """Result of an activity."""

    success: bool
    message: str
    time_advanced: int
    health_change: int = 0
    money_change: int = 0
    experience_gained: dict[str, int] = {}  # skill_name -> xp
    character_xp_gained: int = 0
    character_leveled_up: bool = False
    character_level: int = 1
    attribute_points_gained: int = 0
    skill_progression: dict[
        str, dict
    ] = {}  # skill_name -> {xp_gained, level, leveled_up}
    items_gained: list[dict] = []
    items_lost: list[dict] = []
    new_time_of_day: str
    new_day: int
    narrative: str = ""
    stamina_change: int = 0
    fatigue_change: int = 0
    died: bool = False


class ExploreRequest(BaseModel):
    """Request schema for explore activity."""

    location_id: Optional[int] = Field(
        None, description="Optional specific location to explore"
    )


class ExploreResponse(BaseModel):
    """Response schema for explore activity."""

    result: ActivityResult
    discoveries: list[dict] = []
    encounters: list[dict] = []


class RestRequest(BaseModel):
    """Request schema for rest activity."""

    duration: Literal["short", "long"] = Field(
        "long", description="Rest duration: short (1 period) or long (2 periods)"
    )


class RestResponse(BaseModel):
    """Response schema for rest activity."""

    result: ActivityResult
    health_restored: int
    was_interrupted: bool = False
    interruption_event: Optional[dict] = None


class WorkRequest(BaseModel):
    """Request schema for work activity."""

    work_type: Optional[str] = Field(None, description="Optional specific work type")


class WorkResponse(BaseModel):
    """Response schema for work activity."""

    result: ActivityResult
    work_performed: str
    wages_earned: int


class ActivityListResponse(BaseModel):
    """Response schema for available activities at current location/time."""

    available_activities: list[str]
    location_activities: list[str]
    time_restricted_activities: list[str]
    current_time_of_day: str
    current_location_id: Optional[int]
    current_location_name: Optional[str]
