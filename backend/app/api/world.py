"""World and location API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.exceptions import NotFoundError
from app.models.gameplay import Character, GameplayState
from app.schemas.world import (
    LocationDetailResponse,
    LocationListResponse,
    LocationResponse,
    TravelRequest,
    TravelResponse,
    WorldOverviewResponse,
)
from app.services.character.creation import get_or_create_session
from app.services.world import (
    get_location_detail,
    get_locations,
    get_world_overview,
    travel_to_location,
)

router = APIRouter(tags=["world"], prefix="/world")


def _build_location_response(location) -> LocationResponse:
    """Build location response with region name."""
    return LocationResponse(
        id=location.id,
        name=location.name,
        region_id=location.region_id,
        region_name=location.region.name.value if location.region else "Unknown",
        description=location.description,
        location_type=location.location_type,
        danger_level=location.danger_level,
        population=location.population,
        has_guild=location.has_guild,
        has_market=location.has_market,
        has_inn=location.has_inn,
        available_activities=location.available_activities or [],
    )


def _build_npc_summary(npc) -> dict:
    """Build NPC summary for location detail."""
    return {
        "id": npc.id,
        "name": npc.name,
        "race_name": npc.race_name.value,
        "occupation": npc.occupation,
        "personality": npc.personality.value,
        "description": npc.description,
    }


@router.get("/overview", response_model=WorldOverviewResponse)
async def get_world_overview_endpoint(
    session: AsyncSession = Depends(get_db_session),
) -> WorldOverviewResponse:
    """Get world overview with kingdom, regions, and locations summary."""
    data = await get_world_overview(session)

    kingdom = data["kingdom"]
    regions_data = data["regions"]

    region_responses = []
    for region_data in regions_data:
        region = region_data["region"]
        region_responses.append(
            {
                "id": region.id,
                "name": region.name.value,
                "display_name": region.display_name,
                "description": region.description,
                "danger_level": region.danger_level,
            }
        )

    return WorldOverviewResponse(
        kingdom_name=kingdom.name,
        kingdom_description=kingdom.description,
        regions=region_responses,
        total_locations=data["total_locations"],
    )


@router.get("/locations", response_model=LocationListResponse)
async def list_locations_endpoint(
    region_id: int | None = None,
    location_type: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> LocationListResponse:
    """List all locations, optionally filtered by region and type."""
    locations = await get_locations(
        session=session,
        region_id=region_id,
        location_type=location_type,
    )

    location_responses = [_build_location_response(loc) for loc in locations]

    return LocationListResponse(
        locations=location_responses,
        total=len(location_responses),
    )


@router.get("/locations/{location_id}", response_model=LocationDetailResponse)
async def get_location_detail_endpoint(
    location_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> LocationDetailResponse:
    """Get detailed information about a specific location including NPCs and connected locations."""
    data = await get_location_detail(session, location_id)

    location = data["location"]
    npcs = data["npcs"]
    connected = data["connected_locations"]

    location_response = _build_location_response(location)
    npc_summaries = [_build_npc_summary(npc) for npc in npcs]
    connected_responses = [_build_location_response(loc) for loc in connected]

    return LocationDetailResponse(
        location=location_response,
        npcs=npc_summaries,
        connected_locations=connected_responses,
    )


@router.post("/travel", response_model=TravelResponse)
async def travel_endpoint(
    request: TravelRequest,
    session_token: str,
    session: AsyncSession = Depends(get_db_session),
) -> TravelResponse:
    """Travel to a new location.

    Consumes time based on distance between location types.
    Requires an active game session.
    """
    game_session = await get_or_create_session(session, session_token)

    result = await session.execute(
        select(Character).where(
            Character.session_id == game_session.id,
            Character.generation == game_session.current_generation,
        )
    )
    character = result.scalar_one_or_none()
    if character is None:
        raise NotFoundError("Character", "current generation")

    result = await session.execute(
        select(GameplayState).where(GameplayState.session_id == game_session.id)
    )
    gameplay_state = result.scalar_one_or_none()
    if gameplay_state is None:
        raise NotFoundError("GameplayState", str(game_session.id))

    travel_result = await travel_to_location(
        session=session,
        character=character,
        gameplay_state=gameplay_state,
        target_location_id=request.target_location_id,
    )

    return TravelResponse(**travel_result)
