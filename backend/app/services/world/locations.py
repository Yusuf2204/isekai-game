"""World and location service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.models.enums import TimeOfDay
from app.models.gameplay import Character, GameplayState, NPC
from app.models.world import Kingdom, Location, Region


async def get_kingdom(session: AsyncSession) -> Kingdom:
    """Get the kingdom (Eldoria)."""
    result = await session.execute(select(Kingdom).where(Kingdom.name == "Eldoria"))
    kingdom = result.scalar_one_or_none()
    if kingdom is None:
        raise NotFoundError("Kingdom", "Eldoria")
    return kingdom


async def get_regions(session: AsyncSession, kingdom_id: int) -> list[Region]:
    """Get all regions for a kingdom."""
    result = await session.execute(
        select(Region).where(Region.kingdom_id == kingdom_id).order_by(Region.id)
    )
    return list(result.scalars().all())


async def get_locations(
    session: AsyncSession,
    region_id: int | None = None,
    location_type: str | None = None,
) -> list[Location]:
    """Get locations, optionally filtered by region and type."""
    query = select(Location).options(selectinload(Location.region))
    if region_id:
        query = query.where(Location.region_id == region_id)
    if location_type:
        query = query.where(Location.location_type == location_type)
    query = query.order_by(Location.id)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_location_by_id(session: AsyncSession, location_id: int) -> Location:
    """Get a location by ID with region loaded."""
    result = await session.execute(
        select(Location)
        .options(selectinload(Location.region))
        .where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()
    if location is None:
        raise NotFoundError("Location", str(location_id))
    return location


async def get_location_detail(session: AsyncSession, location_id: int) -> dict:
    """Get detailed location info including NPCs and connected locations."""
    location = await get_location_by_id(session, location_id)

    # Get NPCs at this location
    result = await session.execute(select(NPC).where(NPC.location_id == location_id))
    npcs = list(result.scalars().all())

    # Get connected locations (same region, excluding current)
    result = await session.execute(
        select(Location)
        .options(selectinload(Location.region))
        .where(Location.region_id == location.region_id, Location.id != location_id)
    )
    connected = list(result.scalars().all())

    return {
        "location": location,
        "npcs": npcs,
        "connected_locations": connected,
    }


async def get_world_overview(session: AsyncSession) -> dict:
    """Get world overview with kingdom, regions, and location counts."""
    kingdom = await get_kingdom(session)
    regions = await get_regions(session, kingdom.id)

    # Get all locations
    all_locations = await get_locations(session)

    region_responses = []
    for region in regions:
        region_locations = [loc for loc in all_locations if loc.region_id == region.id]
        region_responses.append(
            {
                "region": region,
                "locations_count": len(region_locations),
            }
        )

    return {
        "kingdom": kingdom,
        "regions": region_responses,
        "total_locations": len(all_locations),
    }


# Travel time costs (in time periods: morning->afternoon = 1, etc.)
TRAVEL_TIME_COSTS = {
    ("city", "city"): 1,
    ("city", "market"): 1,
    ("city", "academy"): 1,
    ("city", "outpost"): 2,
    ("city", "ruins"): 3,
    ("city", "village"): 2,
    ("city", "shrine"): 2,
    ("market", "city"): 1,
    ("market", "market"): 1,
    ("market", "academy"): 1,
    ("market", "outpost"): 2,
    ("market", "ruins"): 3,
    ("market", "village"): 2,
    ("market", "shrine"): 2,
    ("academy", "city"): 1,
    ("academy", "market"): 1,
    ("academy", "academy"): 1,
    ("academy", "outpost"): 2,
    ("academy", "ruins"): 3,
    ("academy", "village"): 2,
    ("academy", "shrine"): 2,
    ("outpost", "city"): 2,
    ("outpost", "market"): 2,
    ("outpost", "academy"): 2,
    ("outpost", "outpost"): 1,
    ("outpost", "ruins"): 1,
    ("outpost", "village"): 2,
    ("outpost", "shrine"): 2,
    ("ruins", "city"): 3,
    ("ruins", "market"): 3,
    ("ruins", "academy"): 3,
    ("ruins", "outpost"): 1,
    ("ruins", "ruins"): 1,
    ("ruins", "village"): 2,
    ("ruins", "shrine"): 2,
    ("village", "city"): 2,
    ("village", "market"): 2,
    ("village", "academy"): 2,
    ("village", "outpost"): 2,
    ("village", "ruins"): 2,
    ("village", "village"): 1,
    ("village", "shrine"): 1,
    ("shrine", "city"): 2,
    ("shrine", "market"): 2,
    ("shrine", "academy"): 2,
    ("shrine", "outpost"): 2,
    ("shrine", "ruins"): 2,
    ("shrine", "village"): 1,
    ("shrine", "shrine"): 1,
}

DEFAULT_TRAVEL_COST = 2


def get_travel_time_cost(from_type: str, to_type: str) -> int:
    """Get travel time cost between location types."""
    return TRAVEL_TIME_COSTS.get((from_type, to_type), DEFAULT_TRAVEL_COST)


async def advance_time(
    session: AsyncSession,
    gameplay_state: GameplayState,
    periods: int,
) -> GameplayState:
    """
    Advance in-game time by the specified number of periods.

    Time periods: MORNING -> AFTERNOON -> EVENING -> NIGHT -> MORNING (next day)
    """
    time_order = [
        TimeOfDay.MORNING,
        TimeOfDay.AFTERNOON,
        TimeOfDay.EVENING,
        TimeOfDay.NIGHT,
    ]
    current_idx = time_order.index(gameplay_state.current_time_of_day)

    new_idx = (current_idx + periods) % 4
    days_advanced = (current_idx + periods) // 4

    gameplay_state.current_time_of_day = time_order[new_idx]
    gameplay_state.current_day += days_advanced

    await session.flush()
    await session.refresh(gameplay_state)
    return gameplay_state


async def travel_to_location(
    session: AsyncSession,
    character: Character,
    gameplay_state: GameplayState,
    target_location_id: int,
) -> dict:
    """
    Travel to a new location.

    Consumes time based on distance/location types.
    Updates GameplayState with new location and time.
    """
    # Validate target location
    target_location = await get_location_by_id(session, target_location_id)

    # Check if already at target
    if gameplay_state.current_location_id == target_location_id:
        raise ValidationError(
            "Already at this location",
            details={"location_id": target_location_id},
        )

    # Calculate travel time
    current_location = None
    if gameplay_state.current_location_id:
        current_location = await get_location_by_id(
            session, gameplay_state.current_location_id
        )

    if current_location:
        travel_cost = get_travel_time_cost(
            current_location.location_type, target_location.location_type
        )
    else:
        travel_cost = DEFAULT_TRAVEL_COST

    # Advance time
    previous_location_id = gameplay_state.current_location_id
    await advance_time(session, gameplay_state, travel_cost)

    # Update location
    gameplay_state.current_location_id = target_location_id

    # Log activity
    gameplay_state.recent_activities.append(
        {
            "type": "travel",
            "from_location_id": previous_location_id,
            "to_location_id": target_location_id,
            "time_cost": travel_cost,
            "day": gameplay_state.current_day,
            "time_of_day": gameplay_state.current_time_of_day.value,
        }
    )
    # Keep only last 20 activities
    if len(gameplay_state.recent_activities) > 20:
        gameplay_state.recent_activities = gameplay_state.recent_activities[-20:]

    await session.commit()
    await session.refresh(gameplay_state)

    return {
        "success": True,
        "message": f"Traveled to {target_location.name}",
        "previous_location_id": previous_location_id,
        "new_location_id": target_location_id,
        "time_advanced": travel_cost,
        "new_time_of_day": gameplay_state.current_time_of_day.value,
        "new_day": gameplay_state.current_day,
    }
