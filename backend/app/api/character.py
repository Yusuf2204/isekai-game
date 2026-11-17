"""Character creation and progression API endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db_session
from app.core.exceptions import NotFoundError, ValidationError
from app.models.gameplay import Character
from app.schemas.character import (
    AttributeAllocateRequest,
    AttributeAllocateResponse,
    AttributePointsResponse,
    CharacterAttributeResponse,
    CharacterCreateRequest,
    CharacterCreateResponse,
    CharacterInventoryItemResponse,
    CharacterResponse,
    CharacterSkillResponse,
    ResourceStatusResponse,
    UnifiedProgressionStatusResponse,
)
from app.services.character.creation import create_character, get_or_create_session
from app.services.character.progression import (
    allocate_attribute_points,
    get_attribute_points,
    get_unified_progression_status,
)
from app.services.character.resources import get_resource_status

router = APIRouter(tags=["character"], prefix="/character")


@router.post(
    "/create",
    response_model=CharacterCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_character_endpoint(
    request: CharacterCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> CharacterCreateResponse:
    """Create a new character.

    The character will be associated with a new or existing game session.
    All starting attributes, skills, and inventory are calculated from the
    selected race and background.
    """
    character, game_session = await create_character(
        session=session,
        name=request.name,
        race_name=request.race_name,
        background_name=request.background_name,
        gender_presentation=request.gender_presentation,
        starting_location_id=request.starting_location_id,
    )

    # Reload character with all relationships
    result = await session.execute(
        select(Character)
        .options(
            selectinload(Character.attributes),
            selectinload(Character.skills),
            selectinload(Character.inventory),
        )
        .where(Character.id == character.id)
    )
    character = result.scalar_one()

    character_response = _build_character_response(character)

    return CharacterCreateResponse(
        character=character_response,
        session_token=game_session.session_token,
        message="Character created successfully",
    )


def _build_character_response(character: Character) -> CharacterResponse:
    """Build character response with loaded relationships."""
    attributes = [
        CharacterAttributeResponse(
            name=attr.name.value,
            base_value=attr.base_value,
            current_value=attr.current_value,
            experience=attr.experience,
        )
        for attr in character.attributes
    ]

    skills = [
        CharacterSkillResponse(
            name=skill.name.value,
            level=skill.level,
            experience=skill.experience,
        )
        for skill in character.skills
    ]

    inventory = [
        CharacterInventoryItemResponse(
            item_id=item.item_id,
            name=item.name,
            description=item.description,
            quantity=item.quantity,
            item_type=item.item_type,
            value=item.value,
            is_equipped=item.is_equipped,
            properties=item.properties,
        )
        for item in character.inventory
    ]

    return CharacterResponse(
        id=character.id,
        session_id=character.session_id,
        generation=character.generation,
        name=character.name,
        race_name=character.race_name.value,
        background_name=character.background_name.value,
        gender_presentation=character.gender_presentation.value,
        age=character.age,
        personality_trait=character.personality_trait,
        personality_description=character.personality_description,
        starting_location_id=character.starting_location_id,
        is_alive=character.is_alive,
        current_health=character.current_health,
        max_health=character.max_health,
        money=character.money,
        reputation=character.reputation,
        noble_favor=character.noble_favor,
        common_favor=character.common_favor,
        attribute_points=character.attribute_points,
        attributes=attributes,
        skills=skills,
        inventory=inventory,
    )


async def _get_character_from_session(
    session: AsyncSession, session_token: str
) -> Character:
    """Get current character from session token."""
    game_session = await get_or_create_session(session, session_token)

    result = await session.execute(
        select(Character)
        .options(selectinload(Character.attributes))
        .where(
            Character.session_id == game_session.id,
            Character.generation == game_session.current_generation,
        )
    )
    character = result.scalar_one_or_none()
    if character is None:
        raise NotFoundError("Character", "current generation")
    if not character.is_alive:
        raise ValidationError(
            "Dead characters cannot allocate attribute points",
            details={"character_id": character.id},
        )
    return character


@router.get("/attribute-points", response_model=AttributePointsResponse)
async def get_attribute_points_endpoint(
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> AttributePointsResponse:
    """Get the current character's unspent attribute points."""
    character = await _get_character_from_session(session, session_token)
    result = await get_attribute_points(character)
    return AttributePointsResponse(**result)


@router.post("/allocate-attribute", response_model=AttributeAllocateResponse)
async def allocate_attribute_endpoint(
    request: AttributeAllocateRequest,
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> AttributeAllocateResponse:
    """Allocate attribute points to increase a character attribute.

    Each allocation consumes 1 Attribute Point (or more if specified).
    Attribute Points are earned through character level-ups (1 per level).
    """
    character = await _get_character_from_session(session, session_token)

    result = await allocate_attribute_points(
        session=session,
        character=character,
        attribute_name=request.attribute_name,
        points=request.points,
    )

    return AttributeAllocateResponse(**result)


@router.get("/progression", response_model=UnifiedProgressionStatusResponse)
async def get_progression_status_endpoint(
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> UnifiedProgressionStatusResponse:
    """Get the complete unified progression status for the current character.

    Returns character level/XP, all skills with progression, and all attributes with values.
    """
    character = await _get_character_from_session(session, session_token)

    # Load skills and attributes if not already loaded
    await session.refresh(character, ["attributes", "skills"])

    result = await get_unified_progression_status(session, character)

    return UnifiedProgressionStatusResponse(**result)


@router.get("/resources", response_model=ResourceStatusResponse)
async def get_resource_status_endpoint(
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> ResourceStatusResponse:
    """Get the current character's resource status.

    Returns health (current, max, percent), alive status, and money.
    """
    character = await _get_character_from_session(session, session_token)

    result = await get_resource_status(character)

    return ResourceStatusResponse(**result)
