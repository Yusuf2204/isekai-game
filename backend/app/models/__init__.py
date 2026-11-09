"""Models package initialization."""

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    TimeOfDay,
    RegionName,
    RaceName,
    BackgroundName,
    NPCPersonality,
    GenderPresentation,
    AttributeName,
    SkillName,
    EnemyType,
    DeathCause,
    LegacyType,
    EventCategory,
    ActivityType,
)
from app.models.world import (
    Kingdom,
    Region,
    Location,
    Race,
    Background,
    Enemy,
)
from app.models.gameplay import (
    GameSession,
    Character,
    CharacterAttribute,
    CharacterSkill,
    InventoryItem,
    NPC,
    NPCRelationship,
    LifeRecord,
    CharacterLegacy,
    GameplayState,
)

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    # Enums
    "TimeOfDay",
    "RegionName",
    "RaceName",
    "BackgroundName",
    "NPCPersonality",
    "GenderPresentation",
    "AttributeName",
    "SkillName",
    "EnemyType",
    "DeathCause",
    "LegacyType",
    "EventCategory",
    "ActivityType",
    # World models
    "Kingdom",
    "Region",
    "Location",
    "Race",
    "Background",
    "Enemy",
    # Gameplay models
    "GameSession",
    "Character",
    "CharacterAttribute",
    "CharacterSkill",
    "InventoryItem",
    "NPC",
    "NPCRelationship",
    "LifeRecord",
    "CharacterLegacy",
    "GameplayState",
]
