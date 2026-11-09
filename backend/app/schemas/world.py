"""World and location schemas."""

from pydantic import BaseModel, Field


class RegionResponse(BaseModel):
    """Response schema for a region."""

    id: int
    name: str
    display_name: str
    description: str
    danger_level: int

    class Config:
        from_attributes = True


class LocationResponse(BaseModel):
    """Response schema for a location."""

    id: int
    name: str
    region_id: int
    region_name: str
    description: str
    location_type: str
    danger_level: int
    population: int
    has_guild: bool
    has_market: bool
    has_inn: bool
    available_activities: list[str]

    class Config:
        from_attributes = True


class LocationListResponse(BaseModel):
    """Response schema for listing locations."""

    locations: list[LocationResponse]
    total: int


class LocationDetailResponse(BaseModel):
    """Detailed response schema for a location including NPCs and connected locations."""

    location: LocationResponse
    npcs: list["NPCSummaryResponse"] = []
    connected_locations: list[LocationResponse] = []

    class Config:
        from_attributes = True


class NPCSummaryResponse(BaseModel):
    """Summary response schema for an NPC."""

    id: int
    name: str
    race_name: str
    occupation: str
    personality: str
    description: str

    class Config:
        from_attributes = True


# Resolve forward references
LocationDetailResponse.model_rebuild()


class WorldOverviewResponse(BaseModel):
    """Response schema for world overview."""

    kingdom_name: str
    kingdom_description: str
    regions: list[RegionResponse]
    total_locations: int


class TravelRequest(BaseModel):
    """Request schema for traveling to a location."""

    target_location_id: int = Field(..., description="ID of the location to travel to")


class TravelResponse(BaseModel):
    """Response schema for travel action."""

    success: bool
    message: str
    previous_location_id: int
    new_location_id: int
    time_advanced: int  # Number of time periods advanced
    new_time_of_day: str
    new_day: int
