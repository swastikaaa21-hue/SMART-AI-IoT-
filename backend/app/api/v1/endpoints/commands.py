"""
Device command endpoints - send commands to IoT devices via MQTT.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.db.session import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.device import DeviceCommandRequest, DeviceCommandResponse
from app.services.device_manager import device_manager
from app.utils.exceptions import BadRequestError, NotFoundError

router = APIRouter()


@router.post("/{device_id}", response_model=DeviceCommandResponse)
async def send_command(
    device_id: str,
    body: DeviceCommandRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a command to a specific device.

    The command is published to the device's MQTT command topic and logged
    in the database.

    Actions: ``turn_on``, ``turn_off``, ``toggle``, ``set_value``, ``get_status``
    """
    result = await device_manager.send_command(
        db=db,
        device_id=device_id,
        action=body.action,
        value=body.value,
        source="api",
    )

    if not result.get("success"):
        error_msg = result.get("error", "Unknown error")
        if "not found" in error_msg.lower():
            raise NotFoundError("Device", device_id)
        raise BadRequestError(error_msg)

    return DeviceCommandResponse(
        device_id=result["device_id"],
        action=result["action"],
        payload_sent=result["payload_sent"],
        status=result["status"],
        message=result["message"],
    )


@router.get("/logs/{device_id}")
async def get_command_logs(
    device_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get command history for a specific device."""
    offset = (page - 1) * page_size
    logs, total = await device_manager.get_command_logs(
        db=db,
        device_id=device_id,
        limit=page_size,
        offset=offset,
    )

    return PaginatedResponse.create(
        items=[
            {
                "id": str(log.id),
                "device_id": log.device_id,
                "action": log.action,
                "payload": log.payload,
                "source": log.source,
                "status": log.status,
                "error_message": log.error_message,
                "executed_at": log.executed_at.isoformat(),
            }
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/logs/")
async def get_all_command_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all command logs across all devices."""
    offset = (page - 1) * page_size
    logs, total = await device_manager.get_command_logs(
        db=db,
        device_id=None,
        limit=page_size,
        offset=offset,
    )

    return PaginatedResponse.create(
        items=[
            {
                "id": str(log.id),
                "device_id": log.device_id,
                "action": log.action,
                "payload": log.payload,
                "source": log.source,
                "status": log.status,
                "error_message": log.error_message,
                "executed_at": log.executed_at.isoformat(),
            }
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
