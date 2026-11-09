"""Time system schemas."""

from pydantic import BaseModel, Field


class TimeStateResponse(BaseModel):
    """Response schema for current in-game time state."""

    current_day: int
    current_time_of_day: str
    time_of_day_display: str
    day_description: str


class AdvanceTimeRequest(BaseModel):
    """Request schema for advancing time."""

    periods: int = Field(
        ..., ge=1, le=4, description="Number of time periods to advance (1-4)"
    )


class AdvanceTimeResponse(BaseModel):
    """Response schema for time advancement."""

    previous_day: int
    previous_time_of_day: str
    new_day: int
    new_time_of_day: str
    periods_advanced: int
    message: str


class TimePeriodInfo(BaseModel):
    """Information about a time period."""

    name: str
    display_name: str
    description: str
    available_activities: list[str]
    npc_availability_modifier: float  # 0.0 to 1.0


class TimePeriodsResponse(BaseModel):
    """Response schema for all time periods info."""

    periods: list[TimePeriodInfo]
    current_period: str
