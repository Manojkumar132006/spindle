"""FastAPI application factory for Spindle."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from spindle.api.v1.router import api_v1_router
from spindle.config import get_settings
from spindle.database import verify_connection


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler for FastAPI startup and shutdown."""
    # Startup actions
    yield
    # Shutdown actions


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Constraint-Driven Narrative Intelligence System",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
    async def root_health():
        """Basic health check endpoint."""
        return {
            "status": "ok",
            "project": settings.PROJECT_NAME,
            "version": "0.1.0",
            "environment": settings.ENVIRONMENT,
        }

    @app.get(f"{settings.API_V1_STR}/health", status_code=status.HTTP_200_OK, tags=["Health"])
    async def api_v1_health():
        """Detailed API v1 health check including database connectivity."""
        try:
            db_connected = await verify_connection()
        except Exception:
            db_connected = False

        status_str = "healthy" if db_connected else "degraded"
        status_code = status.HTTP_200_OK if db_connected else status.HTTP_503_SERVICE_UNAVAILABLE

        return JSONResponse(
            status_code=status_code,
            content={
                "status": status_str,
                "project": settings.PROJECT_NAME,
                "database": "connected" if db_connected else "disconnected",
                "environment": settings.ENVIRONMENT,
            },
        )

    # Mount API v1 routes
    app.include_router(api_v1_router, prefix=settings.API_V1_STR)

    return app


app = create_app()
