"""Time system service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.enums import TimeOfDay
from app.models.gameplay import Character, GameplayState
from app.services.character.conditions import reduce_condition_duration


# Time period descriptions and properties
TIME_PERIOD_INFO = {
    TimeOfDay.MORNING: {
        "display_name": "Morning",
        "description": "The sun rises over Eldoria. Markets open, and the city stirs to life. Good for work, training, and socializing.",
        "available_activities": [
            "work",
            "train",
            "trade",
            "explore",
            "socialize",
            "accept_quest",
            "visit_location",
        ],
        "npc_availability_modifier": 1.0,
    },
    TimeOfDay.AFTERNOON: {
        "display_name": "Afternoon",
        "description": "The day is in full swing. Guilds are busy with contracts, and travelers arrive at inns. Good for quests, hunting, and trading.",
        "available_activities": [
            "work",
            "train",
            "trade",
            "explore",
            "hunt_monsters",
            "accept_quest",
            "visit_location",
        ],
        "npc_availability_modifier": 1.0,
    },
    TimeOfDay.EVENING: {
        "display_name": "Evening",
        "description": "Shadows lengthen. Taverns fill with adventurers sharing tales. Social activities peak, but travel becomes risky.",
        "available_activities": [
            "socialize",
            "rest",
            "trade",
            "explore",
            "visit_location",
        ],
        "npc_availability_modifier": 0.8,
    },
    TimeOfDay.NIGHT: {
        "display_name": "Night",
        "description": "Darkness blankets the land. Most honest folk sleep, but danger and opportunity both lurk in the shadows.",
        "available_activities": ["rest", "explore", "hunt_monsters"],
        "npc_availability_modifier": 0.3,
    },
}


async def get_current_time_state(gameplay_state: GameplayState) -> dict:
    """Get the current time state from gameplay state."""
    current_time = gameplay_state.current_time_of_day
    info = TIME_PERIOD_INFO[current_time]

    return {
        "current_day": gameplay_state.current_day,
        "current_time_of_day": current_time.value,
        "time_of_day_display": info["display_name"],
        "day_description": info["description"],
    }


async def advance_time(
    session: AsyncSession,
    gameplay_state: GameplayState,
    periods: int,
) -> dict:
    """
    Advance in-game time by the specified number of periods.

    Time periods: MORNING -> AFTERNOON -> EVENING -> NIGHT -> MORNING (next day)
    """
    if periods < 1 or periods > 4:
        raise ValidationError(
            "Periods must be between 1 and 4",
            details={"periods": periods},
        )

    time_order = [
        TimeOfDay.MORNING,
        TimeOfDay.AFTERNOON,
        TimeOfDay.EVENING,
        TimeOfDay.NIGHT,
    ]
    current_idx = time_order.index(gameplay_state.current_time_of_day)

    previous_day = gameplay_state.current_day
    previous_time = gameplay_state.current_time_of_day.value

    new_idx = (current_idx + periods) % 4
    days_advanced = (current_idx + periods) // 4

    gameplay_state.current_time_of_day = time_order[new_idx]
    gameplay_state.current_day += days_advanced

    # Reduce condition durations if day advanced
    expired_conditions = []
    if days_advanced > 0:
        # Get character to reduce condition durations
        result = await session.execute(
            select(Character).where(Character.id == gameplay_state.character_id)
        )
        character = result.scalar_one_or_none()
        if character:
            for _ in range(days_advanced):
                expired = await reduce_condition_duration(session, character)
                expired_conditions.extend(expired)

    # Log activity
    gameplay_state.recent_activities.append(
        {
            "type": "time_advance",
            "periods": periods,
            "previous_day": previous_day,
            "previous_time": previous_time,
            "new_day": gameplay_state.current_day,
            "new_time": gameplay_state.current_time_of_day.value,
        }
    )
    # Keep only last 20 activities
    if len(gameplay_state.recent_activities) > 20:
        gameplay_state.recent_activities = gameplay_state.recent_activities[-20:]

    await session.flush()
    await session.refresh(gameplay_state)

    info = TIME_PERIOD_INFO[gameplay_state.current_time_of_day]

    return {
        "previous_day": previous_day,
        "previous_time_of_day": previous_time,
        "new_day": gameplay_state.current_day,
        "new_time_of_day": gameplay_state.current_time_of_day.value,
        "periods_advanced": periods,
        "days_advanced": days_advanced,
        "expired_conditions": expired_conditions,
        "message": f"Time advanced to {info['display_name']} of Day {gameplay_state.current_day}",
    }


async def get_all_time_periods() -> list[dict]:
    """Get information about all time periods."""
    periods = []
    for time_of_day, info in TIME_PERIOD_INFO.items():
        periods.append(
            {
                "name": time_of_day.value,
                "display_name": info["display_name"],
                "description": info["description"],
                "available_activities": info["available_activities"],
                "npc_availability_modifier": info["npc_availability_modifier"],
            }
        )
    return periods


def get_available_activities_for_time(time_of_day: TimeOfDay) -> list[str]:
    """Get available activities for a specific time of day."""
    return TIME_PERIOD_INFO[time_of_day]["available_activities"]


def get_npc_availability_modifier(time_of_day: TimeOfDay) -> float:
    """Get NPC availability modifier for a specific time of day."""
    return TIME_PERIOD_INFO[time_of_day]["npc_availability_modifier"]
