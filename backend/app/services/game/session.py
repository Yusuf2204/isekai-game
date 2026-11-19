"""Authoritative domain service for Game Session lifecycle, summary, and history."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.models.enums import DeathCause
from app.models.gameplay import (
    Character,
    CharacterLegacy,
    CharacterSkill,
    GameSession,
)
from app.services.reincarnation.death import record_death


async def get_session_summary(
    session: AsyncSession, session_token: str
) -> dict[str, Any]:
    """
    Compile the authoritative session summary across all generations per SPEC.md §10.

    Gathers total generations, characters created, death records, legacies passed,
    skills developed, important decisions, and life achievements.
    """
    token = session_token.strip() if session_token else ""
    if not token:
        raise ValidationError(
            "Session token cannot be empty or whitespace",
            details={"session_token": session_token},
        )

    session_res = await session.execute(
        select(GameSession)
        .where(GameSession.session_token == token)
        .options(
            selectinload(GameSession.characters),
            selectinload(GameSession.life_records),
            selectinload(GameSession.gameplay_state),
        )
    )
    game_session = session_res.scalar_one_or_none()
    if game_session is None:
        raise NotFoundError("GameSession", session_token)

    # Gather characters
    sorted_characters = sorted(game_session.characters, key=lambda c: c.generation)
    char_ids = [c.id for c in sorted_characters]

    # Gather legacies passed
    legacies_passed: list[CharacterLegacy] = []
    if char_ids:
        leg_res = await session.execute(
            select(CharacterLegacy)
            .where(CharacterLegacy.character_id.in_(char_ids))
            .order_by(CharacterLegacy.id.asc())
        )
        legacies_passed = list(leg_res.scalars().all())

    # Build character snapshots
    characters_created = [
        {
            "character_id": c.id,
            "generation": c.generation,
            "name": c.name,
            "race_name": c.race_name.value
            if hasattr(c.race_name, "value")
            else str(c.race_name),
            "background_name": (
                c.background_name.value
                if hasattr(c.background_name, "value")
                else str(c.background_name)
            ),
            "gender_presentation": (
                c.gender_presentation.value
                if hasattr(c.gender_presentation, "value")
                else str(c.gender_presentation)
            ),
            "is_alive": c.is_alive,
            "age": c.age_at_death if c.age_at_death is not None else c.age,
            "level": c.level,
            "cause_of_death": (
                c.death_cause.value
                if hasattr(c.death_cause, "value")
                else (str(c.death_cause) if c.death_cause else None)
            ),
            "death_description": c.death_description,
        }
        for c in sorted_characters
    ]

    # Aggregate skills developed across all lives
    skills_developed: dict[str, int] = {}
    for lr in game_session.life_records:
        for sk_name, sk_lvl in (lr.final_skills or {}).items():
            skills_developed[sk_name] = max(skills_developed.get(sk_name, 0), sk_lvl)

    if char_ids:
        sk_res = await session.execute(
            select(CharacterSkill).where(CharacterSkill.character_id.in_(char_ids))
        )
        for sk in sk_res.scalars().all():
            name_str = sk.name.value if hasattr(sk.name, "value") else str(sk.name)
            skills_developed[name_str] = max(
                skills_developed.get(name_str, 0), sk.level
            )

    # Aggregate decisions
    important_decisions: list[dict[str, Any]] = []
    for lr in game_session.life_records:
        if lr.important_decisions:
            important_decisions.extend(lr.important_decisions)

    if game_session.gameplay_state and game_session.gameplay_state.recent_activities:
        for act in game_session.gameplay_state.recent_activities:
            if act not in important_decisions:
                important_decisions.append(act)

    # Aggregate unique achievements
    achievements_set: set[str] = set()
    for lr in game_session.life_records:
        for ach in lr.achievements or []:
            achievements_set.add(ach)
    if not achievements_set:
        achievements_set.add("Eldorian Citizen")

    # Time lived calculation
    days_from_records = sum(lr.days_lived for lr in game_session.life_records)
    current_life_days = (
        game_session.gameplay_state.current_day
        if (game_session.gameplay_state and any(c.is_alive for c in sorted_characters))
        else 0
    )
    total_time_lived = max(
        game_session.total_time_lived, days_from_records + current_life_days, 1
    )

    sorted_life_records = sorted(game_session.life_records, key=lambda r: r.generation)

    return {
        "session_id": game_session.id,
        "session_token": game_session.session_token,
        "seed": game_session.seed,
        "is_active": game_session.is_active,
        "total_generations": max(
            game_session.total_generations, len(sorted_characters), 1
        ),
        "total_deaths": game_session.total_deaths,
        "total_time_lived": total_time_lived,
        "created_at": game_session.created_at,
        "ended_at": game_session.ended_at,
        "characters_created": characters_created,
        "death_records": sorted_life_records,
        "legacies_passed": legacies_passed,
        "skills_developed": skills_developed,
        "important_decisions": important_decisions,
        "achievements": sorted(list(achievements_set)),
    }


async def end_session(session: AsyncSession, session_token: str) -> dict[str, Any]:
    """
    Conclude an active game session, retire any living character, and return final summary.
    """
    token = session_token.strip() if session_token else ""
    if not token:
        raise ValidationError(
            "Session token cannot be empty or blank",
            details={"session_token": session_token},
        )

    session_res = await session.execute(
        select(GameSession).where(GameSession.session_token == token)
    )
    game_session = session_res.scalar_one_or_none()
    if game_session is None:
        raise NotFoundError("GameSession", session_token)

    if game_session.is_active:
        # Check if current character is still alive; retire peacefully
        living_char_res = await session.execute(
            select(Character).where(
                Character.session_id == game_session.id,
                Character.is_alive.is_(True),
            )
        )
        living_char = living_char_res.scalar_one_or_none()
        if living_char is not None:
            await record_death(
                session=session,
                character_id=living_char.id,
                cause=DeathCause.OLD_AGE,
                death_description=f"{living_char.name} peacefully retired at the journey's conclusion.",
            )

        game_session.is_active = False
        game_session.ended_at = datetime.now(timezone.utc)
        await session.flush()

    return await get_session_summary(session, session_token)


async def list_session_history(
    session: AsyncSession, limit: int = 50
) -> list[dict[str, Any]]:
    """List historical game sessions ordered chronologically descending."""
    result = await session.execute(
        select(GameSession)
        .order_by(GameSession.created_at.desc())
        .limit(max(1, min(limit, 100)))
    )
    sessions = result.scalars().all()
    return [
        {
            "session_id": s.id,
            "session_token": s.session_token,
            "seed": s.seed,
            "is_active": s.is_active,
            "total_generations": s.total_generations,
            "total_deaths": s.total_deaths,
            "total_time_lived": s.total_time_lived,
            "created_at": s.created_at,
            "ended_at": s.ended_at,
        }
        for s in sessions
    ]
