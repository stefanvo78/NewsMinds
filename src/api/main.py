"""
NewsMinds API - Main FastAPI Application

This is the entry point for the API. It:
- Creates the FastAPI app instance
- Configures middleware (CORS, etc.)
- Includes all routers
- Sets up event handlers (startup/shutdown)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.core.config import settings
from src.api.core.database import engine
from src.api.routers import auth, users, sources, articles


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.

    - Startup: Initialize connections
    - Shutdown: Close connections gracefully

    Note: Database tables are managed by Alembic migrations.
    Run 'alembic upgrade head' before starting the app.
    """
    # Startup
    print(f"Starting {settings.APP_NAME}...")
    yield
    # Shutdown
    print(f"Shutting down {settings.APP_NAME}...")
    await engine.dispose()


# Create the FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered news intelligence platform",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# Configure CORS (Cross-Origin Resource Sharing)
# This allows frontend apps on different domains to call our API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with API version prefix
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(sources.router, prefix=settings.API_V1_PREFIX)
app.include_router(articles.router, prefix=settings.API_V1_PREFIX)


# Health check endpoint (no auth required)
@app.get("/health")
async def health_check():
    """
    Health check endpoint for load balancers and container orchestrators.

    Returns 200 OK if the service is running.
    """
    return {"status": "healthy", "service": settings.APP_NAME}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "service": settings.APP_NAME,
        "docs": f"{settings.API_V1_PREFIX}/docs",
        "health": "/health",
    }
