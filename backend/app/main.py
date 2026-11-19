"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import close_db, get_session, init_db
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.api.health import router as health_router
from app.api.character import router as character_router
from app.api.world import router as world_router
from app.api.time import router as time_router
from app.api.activities import router as activities_router
from app.api.conditions import router as conditions_router
from app.api.inventory import router as inventory_router
from app.api.events import router as events_router
from app.api.npc import router as npc_router
from app.api.combat import router as combat_router
from app.api.reincarnation import router as reincarnation_router
from app.api.session import router as session_router
from app.services.world.seed import is_world_fully_seeded, seed_world

logger = logging.getLogger("isekai.api")


async def seed_world_at_startup() -> dict | None:
    """Run world seeding at application startup inside one explicit composition-root transaction.

    Idempotent: does not duplicate entities if already seeded.
    Does not call recreate_db().
    """
    async with get_session() as session:
        if not await is_world_fully_seeded(session):
            logger.info(
                "Database requires world static data seeding; running seed_world..."
            )
            summary = await seed_world(session)
            logger.info("World static data seeded successfully at startup.")
            return summary
        logger.debug("Database already contains all required world static data.")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    setup_logging()
    await init_db()
    await seed_world_at_startup()
    yield
    # Shutdown
    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Isekai: A Life Unwritten",
        description="Single-player Text-Based RPG API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handlers
    register_error_handlers(app)

    # Include routers
    app.include_router(health_router, prefix="/api")
    app.include_router(character_router, prefix="/api")
    app.include_router(world_router, prefix="/api")
    app.include_router(time_router, prefix="/api")
    app.include_router(activities_router, prefix="/api")
    app.include_router(conditions_router, prefix="/api")
    app.include_router(inventory_router, prefix="/api")
    app.include_router(events_router, prefix="/api")
    app.include_router(npc_router, prefix="/api")
    app.include_router(combat_router, prefix="/api")
    app.include_router(reincarnation_router, prefix="/api")
    app.include_router(session_router, prefix="/api")

    return app


app = create_app()
