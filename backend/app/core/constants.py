"""Application constants and game mechanics definitions.

Centralizes game numbers, default thresholds, and scaling bounds to avoid magic numbers
as mandated by AGENTS.md §2 and ROADMAP.md IF-09.
"""

# World and Travel Constants
DEFAULT_TRAVEL_COST = 2

# Character Base Attributes & Progression
DEFAULT_STARTING_AGE = 18
DEFAULT_HEALTH = 100
DEFAULT_STAMINA = 100
DEFAULT_FATIGUE = 0

MIN_ATTRIBUTE_VALUE = 1
BASE_ATTRIBUTE_MAX = 20
MAX_ATTRIBUTE_VALUE = 30
RACIAL_MODIFIER_MAX = 5
BASE_POINTS_POOL = 10

# Financial
BASE_STARTING_MONEY = 50

# Resource Percentages & Bounds
MIN_PERCENTAGE = 0.0
MAX_PERCENTAGE = 100.0
MAX_FATIGUE = 100

# Time Engine
PERIODS_PER_DAY = 4

# Multi-Life & Session
MIN_GENERATIONS = 2
