"""API package initialization."""

from app.api.health import router as health_router
from app.api.character import router as character_router
from app.api.world import router as world_router
from app.api.time import router as time_router
from app.api.activities import router as activities_router

__all__ = [
    "health_router",
    "character_router",
    "world_router",
    "time_router",
    "activities_router",
]
