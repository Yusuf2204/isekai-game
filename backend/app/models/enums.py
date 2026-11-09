"""Enumeration types for the game models."""

import enum


class TimeOfDay(str, enum.Enum):
    """In-game time periods."""

    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"


class RegionName(str, enum.Enum):
    """Regions in the kingdom of Eldoria."""

    AETHERIA = "aetheria"
    VALDREN = "valdren"
    ELARION = "elarion"


class RaceName(str, enum.Enum):
    """Playable races."""

    HUMAN = "human"
    ELF = "elf"
    BEASTKIN = "beastkin"
    DWARF = "dwarf"
    DRAGONKIN = "dragonkin"
    DEMONKIN = "demonkin"


class BackgroundName(str, enum.Enum):
    """Character backgrounds."""

    COMMONER = "commoner"
    MERCHANT_FAMILY = "merchant_family"
    ORPHAN = "orphan"
    NOBLE_DESCENDANT = "noble_descendant"
    FORMER_SLAVE = "former_slave"


class NPCPersonality(str, enum.Enum):
    """NPC personality types."""

    FRIENDLY = "friendly"
    SUSPICIOUS = "suspicious"
    GREEDY = "greedy"
    COMPASSIONATE = "compassionate"
    ARROGANT = "arrogant"
    MANIPULATIVE = "manipulative"


class GenderPresentation(str, enum.Enum):
    """Gender presentation options."""

    MALE = "male"
    FEMALE = "female"
    NON_BINARY = "non_binary"
    OTHER = "other"


class AttributeName(str, enum.Enum):
    """Primary attribute names."""

    STRENGTH = "strength"
    AGILITY = "agility"
    INTELLIGENCE = "intelligence"
    VITALITY = "vitality"
    LUCK = "luck"


class SkillName(str, enum.Enum):
    """Skill names."""

    SWORDSMANSHIP = "swordsmanship"
    ARCHERY = "archery"
    MAGIC = "magic"
    HEALING = "healing"
    COOKING = "cooking"
    TRADING = "trading"
    CRAFTING = "crafting"
    SURVIVAL = "survival"
    NEGOTIATION = "negotiation"


class EnemyType(str, enum.Enum):
    """Enemy types."""

    SLIME = "slime"
    GOBLIN = "goblin"
    DIRE_WOLF = "dire_wolf"
    SKELETON = "skeleton"
    CORRUPTED_BEAST = "corrupted_beast"


class DeathCause(str, enum.Enum):
    """Causes of death."""

    COMBAT = "combat"
    SEVERE_INJURIES = "severe_injuries"
    ILLNESS = "illness"
    DANGEROUS_EXPLORATION = "dangerous_exploration"
    EVENT_CONSEQUENCES = "event_consequences"
    OLD_AGE = "old_age"


class LegacyType(str, enum.Enum):
    """Types of legacy that can carry over."""

    ATTRIBUTE_BONUS = "attribute_bonus"
    SKILL_AFFINITY = "skill_affinity"
    FRAGMENTED_MEMORY = "fragmented_memory"
    RECURRING_DREAM = "recurring_dream"
    INHERITED_BONUS = "inherited_bonus"


class EventCategory(str, enum.Enum):
    """Event categories."""

    DAILY_LIFE = "daily_life"
    SOCIAL_ENCOUNTER = "social_encounter"
    ECONOMIC_OPPORTUNITY = "economic_opportunity"
    MONSTER_ENCOUNTER = "monster_encounter"
    COMBAT = "combat"
    TRAVEL = "travel"
    ACCIDENT = "accident"
    ILLNESS = "illness"
    POLITICAL_INCIDENT = "political_incident"
    RARE = "rare"


class ActivityType(str, enum.Enum):
    """Player activity types."""

    EXPLORE = "explore"
    WORK = "work"
    TRADE = "trade"
    TRAIN = "train"
    REST = "rest"
    REST_SHORT = "rest_short"
    SOCIALIZE = "socialize"
    ACCEPT_QUEST = "accept_quest"
    HUNT_MONSTERS = "hunt_monsters"
    VISIT_LOCATION = "visit_location"
