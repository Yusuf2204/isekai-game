"""Character creation service."""

import secrets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import GameStateError, NotFoundError, ValidationError
from app.core.rng import SeededRNG, get_rng
from app.models.enums import (
    AttributeName,
    BackgroundName,
    GenderPresentation,
    LegacyType,
    RaceName,
    SkillName,
    TimeOfDay,
)
from app.models.gameplay import (
    Character,
    CharacterAttribute,
    CharacterLegacy,
    CharacterSkill,
    GameplayState,
    GameSession,
    InventoryItem,
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


def select_random_personality_trait(rng: SeededRNG) -> tuple[str, str]:
    """Select a random personality trait and description using the session RNG."""
    return rng.choice(PERSONALITY_TRAITS)


def resolve_skill_name(
    skill_name_str: str, background_name: BackgroundName
) -> SkillName:
    """Resolve a seed skill name or raise a descriptive ValidationError."""
    try:
        return SkillName(skill_name_str)
    except ValueError as exc:
        raise ValidationError(
            f"Invalid starting skill '{skill_name_str}' for background "
            f"'{background_name.value}'",
            details={
                "background": background_name.value,
                "invalid_skill": skill_name_str,
                "valid_skills": [skill.value for skill in SkillName],
            },
        ) from exc


def validate_starting_skills(background: Background) -> None:
    """Validate every starting skill defined for a background."""
    for skill_name_str in background.starting_skills or {}:
        resolve_skill_name(skill_name_str, background.name)


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
    if session_token is not None:
        token = session_token.strip()
        if not token:
            raise ValidationError(
                "Session token cannot be empty or whitespace",
                details={"session_token": session_token},
            )
        result = await session.execute(
            select(GameSession).where(GameSession.session_token == token)
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
    legacy: CharacterLegacy | None = None,
) -> list[CharacterSkill]:
    """Create character skill records from background starting skills and inherited legacy."""
    char_skills = []
    starting_skills = dict(background.starting_skills or {})

    # If legacy grants skill affinity, apply bonus or add skill
    if legacy and legacy.skill_affinity and legacy.skill_affinity_bonus > 0:
        legacy_skill_name = legacy.skill_affinity.lower()
        if legacy_skill_name in starting_skills:
            starting_skills[legacy_skill_name] += legacy.skill_affinity_bonus
        else:
            starting_skills[legacy_skill_name] = legacy.skill_affinity_bonus

    for skill_name_str, level in starting_skills.items():
        skill_name = resolve_skill_name(skill_name_str, background.name)
        char_skill = CharacterSkill(
            character_id=character.id,
            name=skill_name,
            level=level,
            experience=0,
        )
        session.add(char_skill)
        char_skills.append(char_skill)
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
    validate_starting_skills(background)

    # Get or create session
    game_session = await get_or_create_session(session, session_token)

    # If session_token was provided, check reincarnation conditions
    inherited_legacy: CharacterLegacy | None = None
    if session_token is not None:
        # Cannot create character if active character is still alive
        living_char_res = await session.execute(
            select(Character).where(
                Character.session_id == game_session.id,
                Character.is_alive.is_(True),
            )
        )
        living_char = living_char_res.scalar_one_or_none()
        if living_char is not None:
            raise GameStateError(
                f"Cannot reincarnate: active character '{living_char.name}' (Generation {living_char.generation}) is still alive.",
                details={
                    "character_id": living_char.id,
                    "generation": living_char.generation,
                },
            )

        # Retrieve previous generation character and its legacy
        prev_char_res = await session.execute(
            select(Character)
            .where(Character.session_id == game_session.id)
            .order_by(Character.generation.desc())
        )
        prev_char = prev_char_res.scalars().first()
        if prev_char is not None:
            next_generation = prev_char.generation + 1
            legacy_res = await session.execute(
                select(CharacterLegacy).where(
                    CharacterLegacy.character_id == prev_char.id
                )
            )
            inherited_legacy = legacy_res.scalar_one_or_none()
        else:
            next_generation = game_session.current_generation
        game_session.current_generation = next_generation
    else:
        next_generation = 1
        game_session.current_generation = 1

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

    # Generate personality using the session's deterministic RNG
    personality_trait, personality_description = select_random_personality_trait(
        get_rng(game_session.seed + next_generation * 101)
    )
    if inherited_legacy:
        if inherited_legacy.recurring_dream:
            personality_description += f" {inherited_legacy.recurring_dream}"
        elif inherited_legacy.memory_fragment:
            personality_description += f" {inherited_legacy.memory_fragment}"

    # Calculate attributes with inherited legacy bonus
    attributes = await calculate_starting_attributes(race, background)
    if (
        inherited_legacy
        and inherited_legacy.attribute_bonus
        and inherited_legacy.attribute_bonus_value > 0
    ):
        try:
            target_attr = AttributeName(inherited_legacy.attribute_bonus.lower())
            if target_attr in attributes:
                attributes[target_attr] += inherited_legacy.attribute_bonus_value
        except ValueError:
            pass

    # Calculate health and stamina incorporating any legacy attribute bonuses
    max_health = await calculate_starting_health(attributes)
    max_stamina = await calculate_starting_stamina(attributes)

    # Starting money with inherited keepsake bonus if present
    starting_money = background.starting_money
    if inherited_legacy and inherited_legacy.legacy_type == LegacyType.INHERITED_BONUS:
        starting_money += 25

    # Create character with social modifiers from background
    character = Character(
        session_id=game_session.id,
        generation=next_generation,
        name=name,
        race_name=race_name,
        background_name=background_name,
        gender_presentation=gender_presentation,
        age=DEFAULT_STARTING_AGE,
        personality_trait=personality_trait,
        personality_description=personality_description,
        starting_location_id=starting_location_id,
        legacy_id=inherited_legacy.id if inherited_legacy else None,
        is_alive=True,
        current_health=max_health,
        max_health=max_health,
        current_stamina=max_stamina,
        max_stamina=max_stamina,
        fatigue_level=0,
        conditions={},
        money=starting_money,
        # Social modifiers from background
        reputation=background.reputation_modifier,
        noble_favor=background.noble_favor,
        common_favor=background.common_favor,
    )
    session.add(character)
    await session.flush()

    # Create associated records
    await create_character_attributes(session, character, attributes)
    await create_character_skills(session, character, background, inherited_legacy)
    await create_character_inventory(session, character, background)

    # Create or reset GameplayState for the session
    gp_res = await session.execute(
        select(GameplayState).where(GameplayState.session_id == game_session.id)
    )
    gameplay_state = gp_res.scalar_one_or_none()
    if gameplay_state is not None:
        gameplay_state.character_id = character.id
        gameplay_state.current_location_id = starting_location_id
        gameplay_state.current_time_of_day = TimeOfDay.MORNING
        gameplay_state.current_day = 1
        gameplay_state.in_combat = False
        gameplay_state.combat_enemy_id = None
        gameplay_state.combat_state = {}
        gameplay_state.active_event_id = None
        gameplay_state.event_choices = []
        gameplay_state.recent_activities = []
    else:
        gameplay_state = GameplayState(
            session_id=game_session.id,
            character_id=character.id,
            current_location_id=starting_location_id,
            current_time_of_day=TimeOfDay.MORNING,
            current_day=1,
            in_combat=False,
            combat_enemy_id=None,
            combat_state={},
            active_event_id=None,
            event_choices=[],
            recent_activities=[],
        )
        session.add(gameplay_state)

    # Update session metrics
    game_session.total_generations = max(
        game_session.total_generations, next_generation
    )

    await session.flush()
    await session.refresh(character)

    return character, game_session
