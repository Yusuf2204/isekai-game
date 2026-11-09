"""Character creation service."""

import secrets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.enums import (
    RaceName,
    BackgroundName,
    GenderPresentation,
    AttributeName,
    SkillName,
    TimeOfDay,
)
from app.models.gameplay import (
    Character,
    GameSession,
    CharacterAttribute,
    CharacterSkill,
    InventoryItem,
    GameplayState,
)
from app.models.world import Race, Background, Location


DEFAULT_STARTING_AGE = 18
DEFAULT_HEALTH = 100
DEFAULT_STAMINA = 100

# Personality traits pool for random generation
PERSONALITY_TRAITS = [
    ("Curious", "Always asking questions and seeking to understand the world."),
    ("Cautious", "Thinks carefully before acting, prefers safety over risk."),
    ("Bold", "Acts with confidence and takes risks others wouldn't."),
    ("Compassionate", "Feels deeply for others and helps those in need."),
    ("Ambitious", "Driven to achieve greatness and leave a mark on the world."),
    ("Pragmatic", "Focuses on practical solutions over ideals."),
    ("Whimsical", "Follows intuition and finds joy in the unexpected."),
    (
        "Stoic",
        "Endures hardship without complaint, emotions hidden beneath the surface.",
    ),
    ("Scholarly", "Values knowledge and learning above all else."),
    ("Wanderer", "Never stays in one place long, always seeking the horizon."),
]


def generate_session_token() -> str:
    """Generate a secure session token."""
    return secrets.token_urlsafe(32)


def generate_rng_seed() -> int:
    """Generate a random seed for the RNG."""
    return secrets.randbits(32)


def select_random_personality_trait() -> tuple[str, str]:
    """Select a random personality trait and description."""
    import random

    return random.choice(PERSONALITY_TRAITS)


async def validate_race(session: AsyncSession, race_name: RaceName) -> Race:
    """Validate that the race exists and is playable."""
    result = await session.execute(select(Race).where(Race.name == race_name))
    race = result.scalar_one_or_none()
    if race is None:
        raise NotFoundError("Race", race_name.value)
    return race


async def validate_background(
    session: AsyncSession, background_name: BackgroundName
) -> Background:
    """Validate that the background exists."""
    result = await session.execute(
        select(Background).where(Background.name == background_name)
    )
    background = result.scalar_one_or_none()
    if background is None:
        raise NotFoundError("Background", background_name.value)
    return background


async def validate_location(session: AsyncSession, location_id: int) -> Location:
    """Validate that the location exists."""
    result = await session.execute(select(Location).where(Location.id == location_id))
    location = result.scalar_one_or_none()
    if location is None:
        raise NotFoundError("Location", str(location_id))
    return location


async def get_or_create_session(
    session: AsyncSession, session_token: str | None = None
) -> GameSession:
    """Get existing session by token or create a new one."""
    if session_token:
        result = await session.execute(
            select(GameSession).where(GameSession.session_token == session_token)
        )
        game_session = result.scalar_one_or_none()
        if game_session is None:
            raise NotFoundError("GameSession", session_token)
        if not game_session.is_active:
            raise ValidationError(
                "Game session has ended", details={"session_token": session_token}
            )
        return game_session

    # Create new session
    game_session = GameSession(
        session_token=generate_session_token(),
        seed=generate_rng_seed(),
        current_generation=1,
        total_generations=0,
        is_active=True,
    )
    session.add(game_session)
    await session.flush()
    await session.refresh(game_session)
    return game_session


async def calculate_starting_attributes(
    race: Race,
    background: Background,
) -> dict[AttributeName, int]:
    """Calculate starting attributes from race base + modifiers + background bonuses."""
    race_base = race.get_base_attributes()
    race_mods = race.get_attribute_modifiers()
    bg_bonuses = background.get_attribute_bonuses()

    attributes = {}
    for attr in AttributeName:
        attr_key = attr.value
        base = race_base.get(attr_key, 10)
        mod = race_mods.get(attr_key, 0)
        bonus = bg_bonuses.get(attr_key, 0)
        attributes[attr] = base + mod + bonus

    return attributes


async def calculate_starting_health(attributes: dict[AttributeName, int]) -> int:
    """Calculate starting health based on vitality."""
    vitality = attributes.get(AttributeName.VITALITY, 10)
    # Base health + vitality * 5
    return DEFAULT_HEALTH + (vitality * 5)


async def calculate_starting_stamina(attributes: dict[AttributeName, int]) -> int:
    """Calculate starting stamina based on vitality and agility."""
    vitality = attributes.get(AttributeName.VITALITY, 10)
    agility = attributes.get(AttributeName.AGILITY, 10)
    # Base stamina + vitality * 3 + agility * 2
    return DEFAULT_STAMINA + (vitality * 3) + (agility * 2)


async def create_character_attributes(
    session: AsyncSession,
    character: Character,
    attributes: dict[AttributeName, int],
) -> list[CharacterAttribute]:
    """Create character attribute records."""
    char_attributes = []
    for attr_name, value in attributes.items():
        char_attr = CharacterAttribute(
            character_id=character.id,
            name=attr_name,
            base_value=value,
            current_value=value,
            experience=0,
        )
        session.add(char_attr)
        char_attributes.append(char_attr)
    await session.flush()
    return char_attributes


async def create_character_skills(
    session: AsyncSession,
    character: Character,
    background: Background,
) -> list[CharacterSkill]:
    """Create character skill records from background starting skills."""
    char_skills = []
    starting_skills = background.starting_skills or {}
    for skill_name_str, level in starting_skills.items():
        try:
            skill_name = SkillName(skill_name_str)
            char_skill = CharacterSkill(
                character_id=character.id,
                name=skill_name,
                level=level,
                experience=0,
            )
            session.add(char_skill)
            char_skills.append(char_skill)
        except ValueError:
            # Skip invalid skill names
            continue
    await session.flush()
    return char_skills


async def create_character_inventory(
    session: AsyncSession,
    character: Character,
    background: Background,
) -> list[InventoryItem]:
    """Create character inventory items from background starting items."""
    char_items = []
    starting_items = background.starting_items or []
    for item_name in starting_items:
        char_item = InventoryItem(
            character_id=character.id,
            item_id=item_name.lower()
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", ""),
            name=item_name,
            description=f"Starting item from {background.display_name} background.",
            quantity=1,
            item_type="misc",
            value=0,
            is_equipped=False,
            properties={},
        )
        session.add(char_item)
        char_items.append(char_item)
    await session.flush()
    return char_items


async def create_character(
    session: AsyncSession,
    name: str,
    race_name: RaceName,
    background_name: BackgroundName,
    gender_presentation: GenderPresentation,
    starting_location_id: int | None = None,
    session_token: str | None = None,
) -> tuple[Character, GameSession]:
    """
    Create a new character with all associated data.

    Returns the created character and the game session.
    """
    # Validate inputs
    race = await validate_race(session, race_name)
    background = await validate_background(session, background_name)

    # Get or create session
    game_session = await get_or_create_session(session, session_token)

    # Validate location if provided
    if starting_location_id is not None:
        await validate_location(session, starting_location_id)
    else:
        # Auto-assign a starting location (prefer a city with inn/market)
        result = await session.execute(
            select(Location).where(Location.has_inn).order_by(Location.danger_level)
        )
        default_location = result.scalars().first()
        if default_location:
            starting_location_id = default_location.id

    # Generate personality
    personality_trait, personality_description = select_random_personality_trait()

    # Calculate attributes
    attributes = await calculate_starting_attributes(race, background)

    # Calculate health and stamina
    max_health = await calculate_starting_health(attributes)
    max_stamina = await calculate_starting_stamina(attributes)

    # Create character with social modifiers from background
    character = Character(
        session_id=game_session.id,
        generation=game_session.current_generation,
        name=name,
        race_name=race_name,
        background_name=background_name,
        gender_presentation=gender_presentation,
        age=DEFAULT_STARTING_AGE,
        personality_trait=personality_trait,
        personality_description=personality_description,
        starting_location_id=starting_location_id,
        is_alive=True,
        current_health=max_health,
        max_health=max_health,
        current_stamina=max_stamina,
        max_stamina=max_stamina,
        fatigue_level=0,
        conditions={},
        money=background.starting_money,
        # Social modifiers from background
        reputation=background.reputation_modifier,
        noble_favor=background.noble_favor,
        common_favor=background.common_favor,
    )
    session.add(character)
    await session.flush()

    # Create associated records
    await create_character_attributes(session, character, attributes)
    await create_character_skills(session, character, background)
    await create_character_inventory(session, character, background)

    # Create GameplayState for the session
    gameplay_state = GameplayState(
        session_id=game_session.id,
        character_id=character.id,
        current_location_id=starting_location_id,
        current_time_of_day=TimeOfDay.MORNING,
        current_day=1,
        in_combat=False,
        event_choices=[],
        combat_state={},
        recent_activities=[],
    )
    session.add(gameplay_state)

    # Update session
    game_session.total_generations += 1

    await session.commit()
    await session.refresh(character)

    return character, game_session
