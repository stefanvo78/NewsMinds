"""
NewsMinds API - Main FastAPI Application

This is the entry point for the API. It:
- Creates the FastAPI app instance
- Configures middleware (CORS, etc.)
- Includes all routers
- Sets up event handlers (startup/shutdown)
- Integrates with Azure Monitor for observability
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.core.config import settings
from src.api.core.database import engine
from src.api.core.logging import logger
from src.api.core.rate_limit import limiter
from src.api.routers import auth, users, sources, articles, intelligence
from src.api.routers.collection import router as collection_router


# Azure Monitor integration (only when connection string is provided)
# This enables automatic tracing of requests, dependencies, and exceptions
_azure_monitor_configured = False
if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor()
        _azure_monitor_configured = True
        logger.info("Azure Monitor configured successfully")
    except ImportError:
        logger.warning(
            "azure-monitor-opentelemetry not installed. "
            "Install with: pip install azure-monitor-opentelemetry"
        )
    except Exception as e:
        logger.error(f"Failed to configure Azure Monitor: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.

    - Startup: Initialize connections, log startup
    - Shutdown: Close connections gracefully

    Note: Database tables are managed by Alembic migrations.
    Run 'alembic upgrade head' before starting the app.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME}...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    if _azure_monitor_configured:
        logger.info("Telemetry: Azure Monitor enabled")
    else:
        logger.info("Telemetry: Azure Monitor not configured")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}...")
    await engine.dispose()
    logger.info("Database connections closed")


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

# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Instrument FastAPI with OpenTelemetry (if Azure Monitor is configured)
if _azure_monitor_configured:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumented with OpenTelemetry")
    except ImportError:
        logger.warning("opentelemetry-instrumentation-fastapi not installed")

# Configure CORS (Cross-Origin Resource Sharing)
# This allows frontend apps on different domains to call our API
cors_origins = (
    ["*"] if settings.DEBUG else [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with API version prefix
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(sources.router, prefix=settings.API_V1_PREFIX)
app.include_router(articles.router, prefix=settings.API_V1_PREFIX)
app.include_router(intelligence.router, prefix=settings.API_V1_PREFIX)
app.include_router(collection_router, prefix="/api/v1")


# Health check endpoint (no auth required)
@app.get("/health")
async def health_check():
    """
    Health check endpoint for load balancers and container orchestrators.

    Returns 200 OK if the service is running.
    Used by:
    - Docker HEALTHCHECK
    - Azure Container Apps liveness/readiness probes
    - Load balancers
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
