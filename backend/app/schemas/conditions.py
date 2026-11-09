"""Condition schemas."""

from pydantic import BaseModel


class ConditionResponse(BaseModel):
    """Response schema for a condition."""

    id: str
    name: str
    description: str
    severity: int
    duration: int
    max_duration: int
    stamina_penalty: int
    attribute_penalties: dict[str, int]
    health_per_period: int


class ConditionListResponse(BaseModel):
    """Response schema for character conditions."""

    conditions: list[ConditionResponse]


class TreatmentRequest(BaseModel):
    """Request schema for treating a condition."""

    condition_id: str
    treatment_id: str


class TreatmentResponse(BaseModel):
    """Response schema for treatment result."""

    success: bool
    removed: bool
    old_severity: int
    new_severity: int
    treatment_used: str
    description: str


class ConditionDefinitionResponse(BaseModel):
    """Response schema for condition definition."""

    id: str
    name: str
    description: str
    base_severity: int
    max_duration: int
    health_per_period: int
    stamina_penalty: int
    attribute_penalties: dict[str, int]


class AllConditionsResponse(BaseModel):
    """Response schema for all condition definitions."""

    conditions: list[ConditionDefinitionResponse]


class TreatmentDefinitionResponse(BaseModel):
    """Response schema for treatment definition."""

    id: str
    name: str
    treats: list[str]
    severity_reduction: int
    description: str


class AllTreatmentsResponse(BaseModel):
    """Response schema for all treatment definitions."""

    treatments: list[TreatmentDefinitionResponse]
