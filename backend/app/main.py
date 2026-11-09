"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api.health import router as health_router
from app.api.character import router as character_router
from app.api.world import router as world_router
from app.api.time import router as time_router
from app.api.activities import router as activities_router
from app.api.conditions import router as conditions_router
from app.api.inventory import router as inventory_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await init_db()
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

    # Include routers
    app.include_router(health_router, prefix="/api")
    app.include_router(character_router, prefix="/api")
    app.include_router(world_router, prefix="/api")
    app.include_router(time_router, prefix="/api")
    app.include_router(activities_router, prefix="/api")
    app.include_router(conditions_router, prefix="/api")
    app.include_router(inventory_router, prefix="/api")

    return app


app = create_app()
