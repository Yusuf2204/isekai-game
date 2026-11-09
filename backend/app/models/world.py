"""World models - static data for the game world."""

from typing import TYPE_CHECKING
from sqlalchemy import (
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    RegionName,
    RaceName,
    BackgroundName,
    EnemyType,
)

if TYPE_CHECKING:
    from app.models.gameplay import NPC


class Kingdom(Base, TimestampMixin):
    """Kingdom model - top level world entity."""

    __tablename__ = "kingdoms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    lore: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    regions: Mapped[list["Region"]] = relationship(
        "Region", back_populates="kingdom", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Kingdom(name={self.name})>"


class Region(Base, TimestampMixin):
    """Region model - sub-division of a kingdom."""

    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[RegionName] = mapped_column(Enum(RegionName), nullable=False)
    kingdom_id: Mapped[int] = mapped_column(
        ForeignKey("kingdoms.id", ondelete="CASCADE"), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    danger_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1-5

    # Relationships
    kingdom: Mapped["Kingdom"] = relationship("Kingdom", back_populates="regions")
    locations: Mapped[list["Location"]] = relationship(
        "Location", back_populates="region", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("kingdom_id", "name", name="uq_kingdom_region"),)

    def __repr__(self) -> str:
        return f"<Region(name={self.name.value}, kingdom_id={self.kingdom_id})>"


class Location(Base, TimestampMixin):
    """Location model - explorable places within regions."""

    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # city, village, ruins, forest, etc.
    danger_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1-5
    population: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_guild: Mapped[bool] = mapped_column(default=False, nullable=False)
    has_market: Mapped[bool] = mapped_column(default=False, nullable=False)
    has_inn: Mapped[bool] = mapped_column(default=False, nullable=False)
    available_activities: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )

    # Relationships
    region: Mapped["Region"] = relationship("Region", back_populates="locations")
    npcs: Mapped[list["NPC"]] = relationship(
        "NPC", back_populates="location", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Location(name={self.name}, region_id={self.region_id})>"


class Race(Base, TimestampMixin):
    """Playable race model."""

    __tablename__ = "races"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[RaceName] = mapped_column(Enum(RaceName), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    lore: Mapped[str] = mapped_column(Text, nullable=False)

    # Attribute modifiers (can be negative)
    strength_modifier: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    agility_modifier: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    intelligence_modifier: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    vitality_modifier: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    luck_modifier: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Racial trait
    racial_trait_name: Mapped[str] = mapped_column(String(100), nullable=False)
    racial_trait_description: Mapped[str] = mapped_column(Text, nullable=False)

    # Social implications
    social_stigma: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # -5 to 5, negative = discriminated
    social_privilege: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # 0 to 5

    # Base starting attributes (before modifiers)
    base_strength: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    base_agility: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    base_intelligence: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    base_vitality: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    base_luck: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    def get_attribute_modifiers(self) -> dict[str, int]:
        """Get attribute modifiers as a dictionary."""
        return {
            "strength": self.strength_modifier,
            "agility": self.agility_modifier,
            "intelligence": self.intelligence_modifier,
            "vitality": self.vitality_modifier,
            "luck": self.luck_modifier,
        }

    def get_base_attributes(self) -> dict[str, int]:
        """Get base attributes as a dictionary."""
        return {
            "strength": self.base_strength,
            "agility": self.base_agility,
            "intelligence": self.base_intelligence,
            "vitality": self.base_vitality,
            "luck": self.base_luck,
        }

    def __repr__(self) -> str:
        return f"<Race(name={self.name.value})>"


class Background(Base, TimestampMixin):
    """Character background model."""

    __tablename__ = "backgrounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[BackgroundName] = mapped_column(
        Enum(BackgroundName), unique=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    lore: Mapped[str] = mapped_column(Text, nullable=False)

    # Starting resources
    starting_money: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    starting_items: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )

    # Attribute bonuses
    strength_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    agility_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    intelligence_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vitality_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    luck_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Starting skills (skill_name -> starting_level)
    starting_skills: Mapped[dict[str, int]] = mapped_column(
        JSON, default=dict, nullable=False
    )

    # Social modifiers
    reputation_modifier: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    noble_favor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    common_favor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Available dialogue options (tags)
    dialogue_tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    def get_attribute_bonuses(self) -> dict[str, int]:
        """Get attribute bonuses as a dictionary."""
        return {
            "strength": self.strength_bonus,
            "agility": self.agility_bonus,
            "intelligence": self.intelligence_bonus,
            "vitality": self.vitality_bonus,
            "luck": self.luck_bonus,
        }

    def __repr__(self) -> str:
        return f"<Background(name={self.name.value})>"


class Enemy(Base, TimestampMixin):
    """Enemy type model."""

    __tablename__ = "enemies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[EnemyType] = mapped_column(
        Enum(EnemyType), unique=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    lore: Mapped[str] = mapped_column(Text, nullable=False)

    # Base stats
    base_strength: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    base_agility: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    base_intelligence: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    base_vitality: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    base_luck: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    # Derived stats
    base_health: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    base_attack: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    base_defense: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    base_evasion: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    # Level scaling
    health_per_level: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    attack_per_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    defense_per_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Loot and rewards
    experience_reward: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    money_reward_min: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    money_reward_max: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    possible_loot: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    # Encounter properties
    min_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_level: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    encounter_weight: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False
    )  # For weighted random selection
    preferred_regions: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Enemy(name={self.name.value})>"
