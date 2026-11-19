"""Gameplay models - dynamic data for active game sessions."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    UniqueConstraint,
    Index,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    TimeOfDay,
    RaceName,
    BackgroundName,
    GenderPresentation,
    AttributeName,
    SkillName,
    DeathCause,
    LegacyType,
    NPCPersonality,
)

if TYPE_CHECKING:
    from app.models.world import Location


class GameSession(Base, TimestampMixin):
    """Game session model - tracks a player's overall session across lives."""

    __tablename__ = "game_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    seed: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # RNG seed for reproducibility

    # Session state
    current_generation: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_generations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Session summary data
    total_time_lived: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # in days
    total_deaths: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    characters: Mapped[list["Character"]] = relationship(
        "Character", back_populates="session", cascade="all, delete-orphan"
    )
    life_records: Mapped[list["LifeRecord"]] = relationship(
        "LifeRecord", back_populates="session", cascade="all, delete-orphan"
    )
    gameplay_state: Mapped[Optional["GameplayState"]] = relationship(
        "GameplayState",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<GameSession(id={self.id}, generation={self.current_generation})>"


class Character(Base, TimestampMixin):
    """Character model - represents a single life."""

    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    generation: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Which life number

    # Identity
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    race_name: Mapped[RaceName] = mapped_column(Enum(RaceName), nullable=False)
    background_name: Mapped[BackgroundName] = mapped_column(
        Enum(BackgroundName), nullable=False
    )
    gender_presentation: Mapped[GenderPresentation] = mapped_column(
        Enum(GenderPresentation), nullable=False
    )
    age: Mapped[int] = mapped_column(Integer, default=18, nullable=False)

    # Personality
    personality_trait: Mapped[str] = mapped_column(String(100), nullable=False)
    personality_description: Mapped[str] = mapped_column(Text, nullable=False)

    # Starting location
    starting_location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )

    # Current state
    is_alive: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    current_health: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    max_health: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # Stamina/Energy system
    current_stamina: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    max_stamina: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # Fatigue system
    fatigue_level: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # 0 = no fatigue, higher = more fatigued

    # Conditions (injuries/sickness)
    conditions: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )  # condition_id -> {name, severity, duration, description}

    money: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Character progression
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attribute_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Social modifiers (from background)
    reputation: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    noble_favor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    common_favor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Legacy from previous life (nullable for first generation)
    legacy_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("character_legacies.id", ondelete="SET NULL"), nullable=True
    )

    # Death info (when dead)
    died_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    death_cause: Mapped[Optional[DeathCause]] = mapped_column(
        Enum(DeathCause), nullable=True
    )
    death_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    age_at_death: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    session: Mapped["GameSession"] = relationship(
        "GameSession", back_populates="characters"
    )
    attributes: Mapped[list["CharacterAttribute"]] = relationship(
        "CharacterAttribute", back_populates="character", cascade="all, delete-orphan"
    )
    skills: Mapped[list["CharacterSkill"]] = relationship(
        "CharacterSkill", back_populates="character", cascade="all, delete-orphan"
    )
    inventory: Mapped[list["InventoryItem"]] = relationship(
        "InventoryItem", back_populates="character", cascade="all, delete-orphan"
    )
    npc_relationships: Mapped[list["NPCRelationship"]] = relationship(
        "NPCRelationship", back_populates="character", cascade="all, delete-orphan"
    )
    # Legacy this character created (for the next life)
    legacy_created: Mapped[Optional["CharacterLegacy"]] = relationship(
        "CharacterLegacy",
        back_populates="character",
        foreign_keys="CharacterLegacy.character_id",
        uselist=False,
    )
    # Legacy this character inherited (from previous life)
    inherited_legacy: Mapped[Optional["CharacterLegacy"]] = relationship(
        "CharacterLegacy",
        foreign_keys=[legacy_id],
        uselist=False,
    )
    starting_location: Mapped[Optional["Location"]] = relationship(
        "Location", foreign_keys=[starting_location_id]
    )

    __table_args__ = (
        Index("ix_character_session_generation", "session_id", "generation"),
    )

    def __repr__(self) -> str:
        return f"<Character(name={self.name}, generation={self.generation}, alive={self.is_alive})>"

    @property
    def experience_for_next_level(self) -> int:
        """Calculate experience needed for next level."""
        # Simple formula: level * 100 + 50 (same as skills)
        return self.level * 100 + 50


class CharacterAttribute(Base, TimestampMixin):
    """Character attribute model - the five primary attributes."""

    __tablename__ = "character_attributes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[AttributeName] = mapped_column(Enum(AttributeName), nullable=False)
    base_value: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    current_value: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    character: Mapped["Character"] = relationship(
        "Character", back_populates="attributes"
    )

    __table_args__ = (
        UniqueConstraint("character_id", "name", name="uq_character_attribute"),
    )

    @property
    def experience_for_next_level(self) -> int:
        """Calculate experience needed for next level."""
        return self.current_value * 100 + 50

    def __repr__(self) -> str:
        return f"<CharacterAttribute({self.name.value}={self.current_value})>"


class CharacterSkill(Base, TimestampMixin):
    """Character skill model."""

    __tablename__ = "character_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[SkillName] = mapped_column(Enum(SkillName), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    character: Mapped["Character"] = relationship("Character", back_populates="skills")

    __table_args__ = (
        UniqueConstraint("character_id", "name", name="uq_character_skill"),
    )

    @property
    def experience_for_next_level(self) -> int:
        """Calculate experience needed for next level."""
        # Simple formula: level * 100 + 50
        return self.level * 100 + 50

    def __repr__(self) -> str:
        return (
            f"<CharacterSkill({self.name.value}: Lv.{self.level} XP:{self.experience})>"
        )


class InventoryItem(Base, TimestampMixin):
    """Character inventory item model."""

    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # Reference to item definition
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    item_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # consumable, equipment, material, etc.
    value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_equipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    properties: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    character: Mapped["Character"] = relationship(
        "Character", back_populates="inventory"
    )

    __table_args__ = (
        Index("ix_inventory_character_type", "character_id", "item_type"),
    )

    def __repr__(self) -> str:
        return f"<InventoryItem({self.name} x{self.quantity})>"


class NPC(Base, TimestampMixin):
    """NPC model - important non-player characters."""

    __tablename__ = "npcs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    race_name: Mapped[RaceName] = mapped_column(Enum(RaceName), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    personality: Mapped[NPCPersonality] = mapped_column(
        Enum(NPCPersonality), nullable=False
    )
    occupation: Mapped[str] = mapped_column(String(100), nullable=False)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Description and lore
    description: Mapped[str] = mapped_column(Text, nullable=False)
    background_story: Mapped[str] = mapped_column(Text, nullable=False)

    # Dialogue
    greeting: Mapped[str] = mapped_column(Text, nullable=False)
    dialogue_lines: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    farewell: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationship bounds
    min_relationship: Mapped[int] = mapped_column(Integer, default=-100, nullable=False)
    max_relationship: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # Availability
    available_times: Mapped[list[TimeOfDay]] = mapped_column(
        JSON, default=list, nullable=False
    )  # When NPC can be found
    is_essential: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Cannot be killed/removed

    # Stats (for combat if needed)
    strength: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    agility: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    intelligence: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    vitality: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    # Relationships
    location: Mapped["Location"] = relationship("Location", back_populates="npcs")
    relationships: Mapped[list["NPCRelationship"]] = relationship(
        "NPCRelationship", back_populates="npc", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<NPC(name={self.name}, location_id={self.location_id})>"


class NPCRelationship(Base, TimestampMixin):
    """NPC relationship with a character."""

    __tablename__ = "npc_relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    npc_id: Mapped[int] = mapped_column(
        ForeignKey("npcs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    value: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # -100 to 100
    trust: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0 to 100
    memory_flags: Mapped[dict[str, bool]] = mapped_column(
        JSON, default=dict, nullable=False
    )

    # Relationships
    character: Mapped["Character"] = relationship(
        "Character", back_populates="npc_relationships"
    )
    npc: Mapped["NPC"] = relationship("NPC", back_populates="relationships")

    __table_args__ = (
        UniqueConstraint(
            "character_id", "npc_id", name="uq_character_npc_relationship"
        ),
    )

    def __repr__(self) -> str:
        return f"<NPCRelationship(character_id={self.character_id}, npc_id={self.npc_id}, value={self.value})>"


class LifeRecord(Base, TimestampMixin):
    """Life record - created when a character dies."""

    __tablename__ = "life_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    generation: Mapped[int] = mapped_column(Integer, nullable=False)

    # Character identity snapshot
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    race_name: Mapped[RaceName] = mapped_column(Enum(RaceName), nullable=False)
    background_name: Mapped[BackgroundName] = mapped_column(
        Enum(BackgroundName), nullable=False
    )
    gender_presentation: Mapped[GenderPresentation] = mapped_column(
        Enum(GenderPresentation), nullable=False
    )

    # Death info
    age_at_death: Mapped[int] = mapped_column(Integer, nullable=False)
    cause_of_death: Mapped[DeathCause] = mapped_column(Enum(DeathCause), nullable=False)
    death_description: Mapped[str] = mapped_column(Text, nullable=False)
    days_lived: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Final state snapshot
    final_attributes: Mapped[dict[str, int]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    final_skills: Mapped[dict[str, int]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    final_money: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    final_inventory: Mapped[list[dict]] = mapped_column(
        JSON, default=list, nullable=False
    )
    final_relationships: Mapped[dict[str, int]] = mapped_column(
        JSON, default=dict, nullable=False
    )

    # Achievements and decisions
    important_decisions: Mapped[list[dict]] = mapped_column(
        JSON, default=list, nullable=False
    )
    achievements: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    # Relationships
    session: Mapped["GameSession"] = relationship(
        "GameSession", back_populates="life_records"
    )

    def __repr__(self) -> str:
        return (
            f"<LifeRecord({self.name}, gen={self.generation}, age={self.age_at_death})>"
        )


class CharacterLegacy(Base, TimestampMixin):
    """Character legacy - what carries over to the next life."""

    __tablename__ = "character_legacies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Legacy type and description
    legacy_type: Mapped[LegacyType] = mapped_column(Enum(LegacyType), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Effect data
    attribute_bonus: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # Which attribute
    attribute_bonus_value: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    skill_affinity: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # Which skill
    skill_affinity_bonus: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    # Narrative elements
    memory_fragment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recurring_dream: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    character: Mapped["Character"] = relationship(
        "Character",
        back_populates="legacy_created",
        foreign_keys="CharacterLegacy.character_id",
    )

    def __repr__(self) -> str:
        return f"<CharacterLegacy(type={self.legacy_type.value}, char_id={self.character_id})>"


class GameplayState(Base, TimestampMixin):
    """Current gameplay state for a session."""

    __tablename__ = "gameplay_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Location and time
    current_location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )
    current_time_of_day: Mapped[TimeOfDay] = mapped_column(
        Enum(TimeOfDay), default=TimeOfDay.MORNING, nullable=False
    )
    current_day: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Active event (if any)
    active_event_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_choices: Mapped[list[dict]] = mapped_column(
        JSON, default=list, nullable=False
    )

    # Combat state (if in combat)
    in_combat: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    combat_enemy_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    combat_state: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Recent activity log
    recent_activities: Mapped[list[dict]] = mapped_column(
        JSON, default=list, nullable=False
    )

    # Relationships
    session: Mapped["GameSession"] = relationship(
        "GameSession", back_populates="gameplay_state"
    )
    character: Mapped["Character"] = relationship("Character")
    current_location: Mapped[Optional["Location"]] = relationship("Location")

    def __repr__(self) -> str:
        return f"<GameplayState(session_id={self.session_id}, day={self.current_day}, time={self.current_time_of_day.value})>"
