"""Character creation schemas."""

from pydantic import BaseModel, Field
from app.models.enums import RaceName, BackgroundName, GenderPresentation


class CharacterCreateRequest(BaseModel):
    """Request schema for creating a new character."""

    name: str = Field(..., min_length=1, max_length=100, description="Character name")
    race_name: RaceName = Field(..., description="Character race")
    background_name: BackgroundName = Field(..., description="Character background")
    gender_presentation: GenderPresentation = Field(
        ..., description="Character gender presentation"
    )
    starting_location_id: int | None = Field(
        default=None,
        description="Starting location ID (optional, will be auto-assigned if not provided)",
    )
    session_token: str | None = Field(
        default=None,
        description="Optional session token for reincarnation into next generation",
    )


class CharacterAttributeResponse(BaseModel):
    """Response schema for character attribute."""

    name: str
    base_value: int
    current_value: int
    experience: int = 0


class CharacterSkillResponse(BaseModel):
    """Response schema for character skill."""

    name: str
    level: int
    experience: int = 0


class CharacterInventoryItemResponse(BaseModel):
    """Response schema for character inventory item."""

    item_id: str
    name: str
    description: str
    quantity: int
    item_type: str
    value: int
    is_equipped: bool
    properties: dict


class CharacterResponse(BaseModel):
    """Response schema for character."""

    id: int
    session_id: int
    generation: int
    name: str
    race_name: str
    background_name: str
    gender_presentation: str
    age: int
    personality_trait: str
    personality_description: str
    starting_location_id: int | None
    legacy_id: int | None = None
    is_alive: bool
    current_health: int
    max_health: int
    money: int
    reputation: int = 0
    noble_favor: int = 0
    common_favor: int = 0
    attribute_points: int = 0
    attributes: list[CharacterAttributeResponse] = []
    skills: list[CharacterSkillResponse] = []
    inventory: list[CharacterInventoryItemResponse] = []

    class Config:
        from_attributes = True


class CharacterCreateResponse(BaseModel):
    """Response schema for character creation."""

    character: CharacterResponse
    session_token: str
    message: str = "Character created successfully"


class AttributeAllocateRequest(BaseModel):
    """Request schema for allocating attribute points."""

    attribute_name: str = Field(
        ...,
        description="Attribute to increase (strength, agility, intelligence, vitality, luck)",
    )
    points: int = Field(1, ge=1, description="Number of points to allocate")


class AttributeAllocateResponse(BaseModel):
    """Response schema for attribute allocation."""

    attribute_name: str
    points_allocated: int
    previous_value: int
    new_value: int
    remaining_points: int
    message: str = "Attribute points allocated successfully"


class AttributePointsResponse(BaseModel):
    """Response schema for attribute points status."""

    attribute_points: int


class SkillProgressionResponse(BaseModel):
    """Response schema for skill progression."""

    name: str
    level: int
    experience: int
    experience_for_next_level: int
    progress_percent: float


class AttributeProgressionResponse(BaseModel):
    """Response schema for attribute progression."""

    name: str
    base_value: int
    current_value: int
    experience: int


class CharacterProgressionResponse(BaseModel):
    """Response schema for character progression."""

    level: int
    experience: int
    experience_for_next_level: int
    progress_percent: float
    attribute_points: int


class UnifiedProgressionStatusResponse(BaseModel):
    """Response schema for unified progression status."""

    character: CharacterProgressionResponse
    skills: list[SkillProgressionResponse]
    attributes: list[AttributeProgressionResponse]


class HealthStatusResponse(BaseModel):
    """Response schema for health status."""

    current: int
    max: int
    percent: float


class StaminaStatusResponse(BaseModel):
    """Response schema for stamina status."""

    current: int
    max: int
    effective_max: int
    percent: float


class FatigueStatusResponse(BaseModel):
    """Response schema for fatigue status."""

    level: int
    max: int
    percent: float


class PenaltyStatusResponse(BaseModel):
    """Response schema for penalties."""

    stamina_penalty: int
    attribute_penalties: dict[str, int]


class ResourceStatusResponse(BaseModel):
    """Response schema for complete resource status."""

    health: HealthStatusResponse
    stamina: StaminaStatusResponse
    fatigue: FatigueStatusResponse
    is_alive: bool
    money: int
    penalties: PenaltyStatusResponse


class RaceSummaryResponse(BaseModel):
    """Summary response for playable races."""

    name: str
    display_name: str
    description: str
    lore: str
    strength_modifier: int
    agility_modifier: int
    intelligence_modifier: int
    vitality_modifier: int
    luck_modifier: int
    racial_trait_name: str
    racial_trait_description: str


class BackgroundSummaryResponse(BaseModel):
    """Summary response for character backgrounds."""

    name: str
    display_name: str
    description: str
    starting_money: int
    starting_skills: dict[str, int]
