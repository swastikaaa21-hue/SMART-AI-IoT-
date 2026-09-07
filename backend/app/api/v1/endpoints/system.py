"""
System and configuration endpoints.

Provides endpoints for frontend to fetch backend config, API keys, system status,
MQTT topics, and seed or reset initial smart home data.
"""

from __future__ import annotations

import datetime
from datetime import timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import get_db
from app.middleware.auth import get_current_user, get_current_user_optional
from app.models.device import Device
from app.models.room import Room
from app.models.user import User
from app.schemas.system import (
    SeedResponse,
    SystemConfigResponse,
    SystemConfigUpdate,
    SystemStatusResponse,
    SystemTopicItem,
    SystemTopicsResponse,
)
from app.services.gemini_service import gemini_service
from app.services.mqtt_service import mqtt_service
from app.services.seed_service import seed_user_default_data
from app.services.websocket_manager import ws_manager

router = APIRouter()


@router.get("/config", response_model=SystemConfigResponse)
async def get_system_config(
    user: User | None = Depends(get_current_user_optional),
) -> SystemConfigResponse:
    """
    Retrieve backend system configuration including API keys.
    Allows the frontend to pull current backend settings and API keys seamlessly.
    """
    return SystemConfigResponse(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        app_env=settings.APP_ENV,
        api_v1_prefix=settings.API_V1_PREFIX,
        gemini_api_key=settings.GEMINI_API_KEY,
        gemini_model=settings.GEMINI_MODEL,
        gemini_temperature=settings.GEMINI_TEMPERATURE,
        gemini_max_tokens=settings.GEMINI_MAX_TOKENS,
        gemini_configured=bool(settings.GEMINI_API_KEY and gemini_service._initialised),
        mqtt_broker=settings.MQTT_BROKER,
        mqtt_port=settings.MQTT_PORT,
        mqtt_username=settings.MQTT_USERNAME,
        mqtt_tls_enabled=settings.MQTT_TLS_ENABLED,
        mqtt_connected=mqtt_service.is_connected,
        jwt_access_token_expire_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.post("/config", response_model=SystemConfigResponse)
async def update_system_config(
    body: SystemConfigUpdate,
    user: User = Depends(get_current_user),
) -> SystemConfigResponse:
    """
    Update runtime backend configuration (e.g. Gemini API Key, Model, MQTT parameters).
    Instantly reconfigures Gemini AI service and runtime settings.
    """
    if body.gemini_api_key is not None:
        settings.GEMINI_API_KEY = body.gemini_api_key.strip()
    if body.gemini_model is not None:
        settings.GEMINI_MODEL = body.gemini_model.strip()
    if body.gemini_temperature is not None:
        settings.GEMINI_TEMPERATURE = body.gemini_temperature
    if body.gemini_max_tokens is not None:
        settings.GEMINI_MAX_TOKENS = body.gemini_max_tokens

    if body.mqtt_broker is not None:
        settings.MQTT_BROKER = body.mqtt_broker.strip()
    if body.mqtt_port is not None:
        settings.MQTT_PORT = body.mqtt_port
    if body.mqtt_username is not None:
        settings.MQTT_USERNAME = body.mqtt_username.strip()
    if body.mqtt_password is not None:
        settings.MQTT_PASSWORD = body.mqtt_password

    # Re-initialise Gemini AI with new credentials
    gemini_service.update_config(
        api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_MODEL,
        temperature=settings.GEMINI_TEMPERATURE,
        max_tokens=settings.GEMINI_MAX_TOKENS,
    )

    return SystemConfigResponse(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        app_env=settings.APP_ENV,
        api_v1_prefix=settings.API_V1_PREFIX,
        gemini_api_key=settings.GEMINI_API_KEY,
        gemini_model=settings.GEMINI_MODEL,
        gemini_temperature=settings.GEMINI_TEMPERATURE,
        gemini_max_tokens=settings.GEMINI_MAX_TOKENS,
        gemini_configured=bool(settings.GEMINI_API_KEY and gemini_service._initialised),
        mqtt_broker=settings.MQTT_BROKER,
        mqtt_port=settings.MQTT_PORT,
        mqtt_username=settings.MQTT_USERNAME,
        mqtt_tls_enabled=settings.MQTT_TLS_ENABLED,
        mqtt_connected=mqtt_service.is_connected,
        jwt_access_token_expire_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> SystemStatusResponse:
    """
    Get aggregated system statistics, device counts, and environmental readings.
    """
    # Count rooms
    room_count_res = await db.execute(select(func.count(Room.id)))
    total_rooms = room_count_res.scalar_one()

    # Query all devices for statistics
    dev_res = await db.execute(select(Device))
    devices = list(dev_res.scalars().all())

    total_devices = len(devices)
    online_devices = sum(1 for d in devices if d.is_online)
    active_devices = sum(1 for d in devices if (d.state or "").lower() == "on")

    temps = [d.temperature for d in devices if d.temperature is not None]
    avg_temp = round(sum(temps) / len(temps), 1) if temps else 24.5

    humids = [d.humidity for d in devices if d.humidity is not None]
    avg_humid = round(sum(humids) / len(humids), 1) if humids else 65.0

    return SystemStatusResponse(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        timestamp=datetime.datetime.now(timezone.utc),
        mqtt_connected=mqtt_service.is_connected,
        gemini_ready=gemini_service._initialised,
        ws_active_connections=ws_manager.active_count,
        total_rooms=total_rooms,
        total_devices=total_devices,
        online_devices=online_devices,
        active_devices=active_devices,
        average_temperature=avg_temp,
        average_humidity=avg_humid,
    )


@router.get("/topics", response_model=SystemTopicsResponse)
async def get_system_topics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SystemTopicsResponse:
    """
    List all MQTT topics for devices registered in the system.
    """
    result = await db.execute(
        select(Device).options(selectinload(Device.room))
    )
    devices = list(result.scalars().all())

    topic_items: list[SystemTopicItem] = []
    for d in devices:
        r_slug = d.room.slug if d.room else "unknown"
        topic_items.append(
            SystemTopicItem(
                device_id=d.device_id,
                name=d.name,
                room_slug=r_slug,
                command_topic=f"home/{r_slug}/{d.device_id}/set",
                status_topic=f"home/{r_slug}/{d.device_id}/status",
                telemetry_topic=f"home/{r_slug}/{d.device_id}/telemetry",
            )
        )

    return SystemTopicsResponse(
        broker=settings.MQTT_BROKER,
        port=settings.MQTT_PORT,
        tls=settings.MQTT_TLS_ENABLED,
        status_wildcard="home/+/+/status",
        telemetry_wildcard="home/+/+/telemetry",
        devices=topic_items,
    )


@router.post("/seed", response_model=SeedResponse)
async def seed_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SeedResponse:
    """
    Seed or populate default rooms and devices for the current user.
    """
    rooms_count, devices_count = await seed_user_default_data(db, user.id, reset=False)
    return SeedResponse(
        status="success",
        message=f"Seeded {rooms_count} rooms and {devices_count} devices successfully",
        rooms_count=rooms_count,
        devices_count=devices_count,
    )


@router.post("/reset", response_model=SeedResponse)
async def reset_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SeedResponse:
    """
    Reset and restore the default dashboard rooms and devices.
    """
    rooms_count, devices_count = await seed_user_default_data(db, user.id, reset=True)
    return SeedResponse(
        status="success",
        message="Dashboard restored to initial state",
        rooms_count=rooms_count,
        devices_count=devices_count,
    )
