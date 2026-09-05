"""
SMART AI IoT Backend - Main Application Entry Point

This is the central FastAPI application factory that wires together:
- Database engine (SQLite via async SQLAlchemy)
- MQTT service (HiveMQ Cloud on TLS port 8883)
- Google Gemini AI service (Function Calling)
- WebSocket manager (real-time frontend updates)
- API v1 router with all endpoints
- Middleware stack (CORS, auth, logging, error handling)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import get_logger
from app.middleware.error_handler import (
    ErrorHandlerMiddleware,
    RequestLoggingMiddleware,
    register_error_handlers,
)
from app.schemas.common import HealthResponse
from app.services.gemini_service import gemini_service
from app.services.mqtt_handler import handle_device_status, handle_device_telemetry
from app.services.mqtt_service import mqtt_service
from app.services.websocket_manager import ws_manager

logger = get_logger("main")

# ── Rate Limiter ─────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


# ── Application Lifespan ─────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage startup and shutdown of all backend services.

    Startup:
    1. Initialise Gemini AI
    2. Register MQTT message handlers
    3. Connect to HiveMQ Cloud

    Shutdown:
    1. Disconnect MQTT
    2. Clear AI sessions
    """
    logger.info(
        "app_startup",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        env=settings.APP_ENV,
    )

    # --- Startup ---
    # 1. Initialise Gemini AI
    gemini_service.initialise()

    # 2. Register MQTT message handlers
    mqtt_service.on_status(handle_device_status)
    mqtt_service.on_telemetry(handle_device_telemetry)

    # 3. Connect to MQTT broker
    await mqtt_service.connect()

    logger.info("app_startup_complete")

    yield

    # --- Shutdown ---
    logger.info("app_shutdown_starting")

    await mqtt_service.disconnect()
    gemini_service.clear_all_sessions()

    logger.info("app_shutdown_complete")


# ── Application Factory ─────────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Central Orchestrator Backend for SMART AI IoT Platform. "
            "Connects Frontend (Next.js), Database (SQLite), "
            "Broker (HiveMQ Cloud MQTT TLS), and AI (Google Gemini Function Calling)."
        ),
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # --- Middleware (order matters: last added = first executed) ---

    # Error handler (outermost)
    application.add_middleware(ErrorHandlerMiddleware)

    # Request logging
    application.add_middleware(RequestLoggingMiddleware)

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Custom error handlers
    register_error_handlers(application)

    # --- Routes ---
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # --- Health Check (outside versioned prefix) ---
    @application.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check():
        """System health check endpoint."""
        return HealthResponse(
            status="ok",
            version=settings.APP_VERSION,
            environment=settings.APP_ENV,
            timestamp=datetime.now(timezone.utc),
            services={
                "mqtt": "connected" if mqtt_service.is_connected else "disconnected",
                "gemini": "ready" if gemini_service._initialised else "not_configured",
                "websocket": f"{ws_manager.active_count} connections",
                "database": "configured",
            },
        )

    @application.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs" if settings.DEBUG else "disabled",
            "health": "/health",
            "api": settings.API_V1_PREFIX,
        }

    from fastapi.openapi.utils import get_openapi
    def custom_openapi():
        if application.openapi_schema:
            return application.openapi_schema
        openapi_schema = get_openapi(
            title=application.title,
            version=application.version,
            description=application.description,
            routes=application.routes,
        )
        # Force inject the OAuth2 scheme so Swagger UI shows the Authorize button
        openapi_schema["components"] = openapi_schema.get("components", {})
        openapi_schema["components"]["securitySchemes"] = {
            "OAuth2PasswordBearer": {
                "type": "oauth2",
                "flows": {
                    "password": {
                        "scopes": {},
                        "tokenUrl": "/api/v1/auth/login"
                    }
                }
            }
        }
        # Force all routes to require it except public ones
        for path in openapi_schema.get("paths", {}):
            for method in openapi_schema["paths"][path]:
                if path not in ["/api/v1/auth/login", "/api/v1/auth/register", "/health", "/"]:
                    openapi_schema["paths"][path][method]["security"] = [{"OAuth2PasswordBearer": []}]
        application.openapi_schema = openapi_schema
        return application.openapi_schema

    application.openapi = custom_openapi
    return application


# Create the application instance
app = create_app()
