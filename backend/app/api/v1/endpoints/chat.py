"""
AI Chat endpoints with Gemini Function Calling integration.

Handles natural language interaction with the IoT system through Google Gemini.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.db.session import get_db
from app.middleware.auth import get_current_user
from app.models.chat import ChatMessage, ChatSession
from app.models.device import Device
from app.models.room import Room
from app.models.user import User
from app.schemas.chat import (
    AIChatRequest,
    AIChatResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageResponse,
)
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.services.device_manager import device_manager
from app.services.gemini_service import gemini_service
from app.utils.exceptions import NotFoundError

router = APIRouter()


def _normalize_room_slug(slug_or_name: str | None) -> str:
    if not slug_or_name:
        return ""
    clean = slug_or_name.lower().strip().replace(" ", "-").replace("_", "-")
    aliases = {
        "bedroom": "kamar",
        "kamar-tidur": "kamar",
        "living-room": "ruang-tamu",
        "livingroom": "ruang-tamu",
        "ruang-keluarga": "ruang-tamu",
        "meeting-room": "ruang-rapat",
        "office": "ruang-rapat",
        "ruang-kerja": "ruang-rapat",
    }
    return aliases.get(clean, clean)


async def _execute_function(
    name: str,
    args: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Execute an IoT function requested by Gemini Function Calling.

    This is the bridge between AI intent and actual device operations.
    """
    if name == "control_device":
        dev_id = args.get("device_id", "")
        action = args.get("action", "")
        # Normalize action if natural word was used
        if action in ["nyalakan", "hidupkan", "on"]:
            action = "turn_on"
        elif action in ["matikan", "padamkan", "off"]:
            action = "turn_off"

        result = await device_manager.send_command(
            db=db,
            device_id=dev_id,
            action=action,
            value=args.get("value"),
            source="ai",
        )
        return result

    elif name == "get_device_status":
        device = await device_manager.get_device(db, args.get("device_id", ""))
        if not device:
            return {"error": f"Device '{args.get('device_id')}' not found"}
        return {
            "device_id": device.device_id,
            "name": device.name,
            "state": device.state,
            "is_online": device.is_online,
            "device_type": device.device_type,
            "temperature": device.temperature,
            "humidity": device.humidity,
            "brightness": device.brightness,
            "last_seen_at": str(device.last_seen_at) if device.last_seen_at else None,
        }

    elif name == "list_devices":
        raw_room = args.get("room")
        room_slug = _normalize_room_slug(raw_room) if raw_room else None
        dtype = args.get("device_type")

        room_id = None
        if room_slug:
            result = await db.execute(select(Room).where(Room.slug == room_slug))
            room = result.scalar_one_or_none()
            if room:
                room_id = room.id

        devices, total = await device_manager.list_devices(
            db=db,
            room_id=room_id,
            device_type=dtype,
            page=1,
            page_size=50,
        )
        return {
            "total": total,
            "devices": [
                {
                    "device_id": d.device_id,
                    "name": d.name,
                    "type": d.device_type,
                    "state": d.state,
                    "is_online": d.is_online,
                    "room": str(d.room_id) if d.room_id else None,
                }
                for d in devices
            ],
        }

    elif name == "get_telemetry":
        limit = min(args.get("limit", 10), 100)
        logs, total = await device_manager.get_telemetry(
            db=db,
            device_id=args.get("device_id"),
            limit=limit,
        )
        return {
            "device_id": args.get("device_id"),
            "total_records": total,
            "readings": [
                {
                    "temperature": log.temperature,
                    "humidity": log.humidity,
                    "power_watts": log.power_watts,
                    "recorded_at": log.recorded_at.isoformat(),
                }
                for log in logs
            ],
        }

    elif name == "control_room_devices":
        raw_room = args.get("room", "")
        room_slug = _normalize_room_slug(raw_room)
        action = args.get("action", "")
        if action in ["nyalakan", "hidupkan", "on"]:
            action = "turn_on"
        elif action in ["matikan", "padamkan", "off"]:
            action = "turn_off"
        dtype = args.get("device_type")

        # Find the room by normalized slug or like name
        result = await db.execute(select(Room).where(Room.slug == room_slug))
        room = result.scalar_one_or_none()
        if not room:
            result = await db.execute(select(Room).where(func.lower(Room.name) == raw_room.lower().strip()))
            room = result.scalar_one_or_none()

        if not room:
            return {"error": f"Room '{raw_room}' not found"}

        # Get devices in that room
        query = select(Device).where(Device.room_id == room.id)
        if dtype:
            query = query.where(Device.device_type == dtype)
        device_result = await db.execute(query)
        devices = list(device_result.scalars().all())

        if not devices:
            return {"error": f"No devices found in room '{room.name}'"}

        results = []
        affected_devices = []
        for device in devices:
            cmd_result = await device_manager.send_command(
                db=db,
                device_id=device.device_id,
                action=action,
                source="ai",
            )
            results.append(cmd_result)
            affected_devices.append(device.device_id)

        success_count = sum(1 for r in results if r.get("success"))
        return {
            "room": room.slug,
            "action": action,
            "total_devices": len(devices),
            "success_count": success_count,
            "devices": affected_devices,
        }

    return {"error": f"Unknown function: {name}"}


@router.post("/message", response_model=AIChatResponse)
async def send_chat_message(
    body: AIChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a natural language message to the AI assistant.

    The AI uses Gemini Function Calling to interpret the message and
    execute IoT commands if needed.
    """
    # Get or create a chat session
    if body.session_id:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == body.session_id,
                ChatSession.user_id == user.id,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundError("ChatSession", str(body.session_id))
    else:
        session = ChatSession(
            user_id=user.id,
            title=body.message[:50] + ("..." if len(body.message) > 50 else ""),
        )
        db.add(session)
        await db.flush()

    # Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)
    await db.flush()

    # Create function executor bound to this db session
    async def executor(name: str, args: dict) -> dict:
        return await _execute_function(name, args, db)

    # Process through Gemini
    ai_result = await gemini_service.chat(
        message=body.message,
        session_id=str(session.id),
        function_executor=executor,
    )

    # Save assistant message
    import json
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=ai_result["reply"],
        function_call=ai_result.get("function_called"),
        function_response=json.dumps(ai_result.get("function_result")) if ai_result.get("function_result") else None,
    )
    db.add(assistant_msg)
    await db.flush()

    return AIChatResponse(
        reply=ai_result["reply"],
        session_id=session.id,
        function_called=ai_result.get("function_called"),
        function_result=ai_result.get("function_result"),
        devices_affected=ai_result.get("devices_affected", []),
    )


# ── Chat Session CRUD ───────────────────────────────────────

@router.get("/sessions", response_model=PaginatedResponse[ChatSessionResponse])
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all chat sessions for the current user."""
    base_query = select(ChatSession).where(ChatSession.user_id == user.id)

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    result = await db.execute(
        base_query
        .order_by(ChatSession.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    sessions = list(result.scalars().all())

    return PaginatedResponse.create(
        items=[ChatSessionResponse.model_validate(s) for s in sessions],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    body: ChatSessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session."""
    session = ChatSession(
        user_id=user.id,
        title=body.title,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def get_session_messages(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a chat session."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError("ChatSession", str(session_id))

    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = list(msg_result.scalars().all())
    return [ChatMessageResponse.model_validate(m) for m in messages]


@router.delete("/sessions/{session_id}", response_model=SuccessResponse)
async def delete_session(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat session and all its messages."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError("ChatSession", str(session_id))

    # Clear Gemini's in-memory history
    gemini_service.clear_session(str(session_id))

    await db.delete(session)
    await db.flush()
    return SuccessResponse(message="Chat session deleted successfully")
