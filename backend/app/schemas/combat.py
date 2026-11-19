"""Pydantic schemas for the Combat System."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class CombatEnemySchema(BaseModel):
    """Enemy status in active combat."""

    id: int
    name: str
    display_name: str
    description: str
    current_health: int
    max_health: int
    attack: int
    defense: int
    agility: int


class CombatPlayerStatusSchema(BaseModel):
    """Player character status in active combat."""

    character_id: int
    name: str
    current_health: int
    max_health: int
    current_stamina: int
    max_stamina: int
    is_defending: bool = False


class CombatStartRequest(BaseModel):
    """Request to initiate a combat encounter."""

    session_token: str
    enemy_type: Optional[str] = None
    rng_seed: Optional[int] = None


class CombatStateResponse(BaseModel):
    """Current state of combat for a player character."""

    in_combat: bool
    turn: int = 1
    enemy: Optional[CombatEnemySchema] = None
    player: Optional[CombatPlayerStatusSchema] = None
    player_first: bool = True
    status: str = "active"  # "active" | "victory" | "defeat" | "fled"
    log: list[str] = Field(default_factory=list)
    available_actions: list[str] = Field(
        default_factory=lambda: ["attack", "defend", "use_skill", "use_item", "flee"]
    )


class CombatActionRequest(BaseModel):
    """Request to execute a turn action in combat."""

    session_token: str
    action: str  # "attack" | "defend" | "use_skill" | "use_item" | "flee"
    skill_name: Optional[str] = None
    item_name: Optional[str] = None
    rng_seed: Optional[int] = None


class CombatActionResponse(BaseModel):
    """Result of an action turn in combat."""

    in_combat: bool
    status: str  # "active" | "victory" | "defeat" | "fled"
    turn: int
    player_damage_dealt: int = 0
    enemy_damage_dealt: int = 0
    player: CombatPlayerStatusSchema
    enemy: Optional[CombatEnemySchema] = None
    log_entries: list[str] = Field(default_factory=list)
    victory_rewards: Optional[dict[str, Any]] = None
    death_cause: Optional[str] = None
