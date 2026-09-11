"""
Device manager service.

Central business logic for device state management. Bridges API requests,
MQTT commands, database persistence, and WebSocket notifications.
"""

from __future__ import annotations

import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import CommandAction, DeviceState
from app.core.logging import get_logger
from app.models.command import CommandLog
from app.models.device import Device
from app.models.room import Room
from app.models.telemetry import TelemetryLog
from app.services.mqtt_service import mqtt_service
from app.services.websocket_manager import ws_manager

logger = get_logger("device_manager")


class DeviceManager:
    """Handles all device-related business logic."""

    # ── Device CRUD ──────────────────────────────────────────

    async def list_devices(
        self,
        db: AsyncSession,
        room_id: uuid.UUID | None = None,
        device_type: str | None = None,
        is_online: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Device], int]:
        """List devices with optional filters and pagination."""
        query = select(Device).options(selectinload(Device.room))

        if room_id:
            query = query.where(Device.room_id == room_id)
        if device_type:
            query = query.where(Device.device_type == device_type)
        if is_online is not None:
            query = query.where(Device.is_online == is_online)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()

        # Paginate
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        devices = list(result.scalars().all())

        return devices, total

    async def get_device(self, db: AsyncSession, device_id: str) -> Device | None:
        """Get a single device by its device_id string or matching name/alias."""
        if not device_id:
            return None

        # 1. Exact device_id match
        result = await db.execute(
            select(Device)
            .where(Device.device_id == device_id)
            .options(selectinload(Device.room))
        )
        dev = result.scalar_one_or_none()
        if dev:
            return dev

        # 2. Case-insensitive device_id match
        result = await db.execute(
            select(Device)
            .where(func.lower(Device.device_id) == device_id.lower())
            .options(selectinload(Device.room))
        )
        dev = result.scalar_one_or_none()
        if dev:
            return dev

        # 3. Fallback: match by exact name or slugified name
        clean_name = device_id.lower().replace("-", " ").replace("_", " ").strip()
        result = await db.execute(
            select(Device)
            .where(func.lower(Device.name) == clean_name)
            .options(selectinload(Device.room))
        )
        dev = result.scalar_one_or_none()
        if dev:
            return dev

        # 4. Smart fuzzy match against all devices
        all_res = await db.execute(
            select(Device).options(selectinload(Device.room))
        )
        all_devices = list(all_res.scalars().all())

        # Substring / partial name match
        for d in all_devices:
            d_name = d.name.lower()
            if clean_name in d_name or d_name in clean_name:
                return d

        # Semantic keywords mapping (Room + Device Type)
        term_map = {
            "light": "light", "lampu": "light", "lamp": "light", "penerangan": "light",
            "ac": "ac", "aircond": "ac", "aircon": "ac", "cooler": "ac", "pendingin": "ac",
            "tv": "tv", "television": "tv", "televisi": "tv",
            "fan": "fan", "kipas": "fan", "exhaust": "fan",
            "curtain": "curtain", "tirai": "curtain", "gorden": "curtain",
            "speaker": "speaker", "soundbar": "speaker", "audio": "speaker",
            "projector": "projector", "proyektor": "projector",
            "kamar": "kamar", "bedroom": "kamar", "bed": "kamar", "tidur": "kamar",
            "tamu": "ruang-tamu", "living": "ruang-tamu", "keluarga": "ruang-tamu",
            "dapur": "dapur", "kitchen": "dapur",
            "rapat": "ruang-rapat", "meeting": "ruang-rapat", "office": "ruang-rapat", "kerja": "ruang-rapat",
        }

        tokens = set(re.findall(r"[a-zA-Z0-9]+", device_id.lower()))
        mapped_types = set()
        mapped_rooms = set()
        for t in tokens:
            if t in term_map:
                val = term_map[t]
                if val in ["light", "ac", "tv", "fan", "curtain", "speaker", "projector"]:
                    mapped_types.add(val)
                else:
                    mapped_rooms.add(val)

        # Match both room and device type
        if mapped_types and mapped_rooms:
            for d in all_devices:
                r_slug = d.room.slug.replace("_", "-") if d.room else ""
                if d.device_type in mapped_types and r_slug in mapped_rooms:
                    return d

        # Match device type if only 1 matching device
        if mapped_types:
            matching = [d for d in all_devices if d.device_type in mapped_types]
            if len(matching) == 1:
                return matching[0]

        return None

    async def get_device_by_uuid(self, db: AsyncSession, device_uuid: uuid.UUID) -> Device | None:
        """Get a single device by its UUID primary key."""
        result = await db.execute(
            select(Device)
            .where(Device.id == device_uuid)
            .options(selectinload(Device.room))
        )
        return result.scalar_one_or_none()

    async def create_device(self, db: AsyncSession, **kwargs: Any) -> Device:
        """Create a new device record."""
        device = Device(**kwargs)
        db.add(device)
        await db.flush()
        await db.refresh(device, attribute_names=["room"])
        logger.info("device_created", device_id=device.device_id, name=device.name)
        return device

    async def update_device(
        self,
        db: AsyncSession,
        device_id: str,
        **kwargs: Any,
    ) -> Device | None:
        """Update device attributes."""
        device = await self.get_device(db, device_id)
        if not device:
            return None

        for key, value in kwargs.items():
            if value is not None and hasattr(device, key):
                setattr(device, key, value)

        device.updated_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(device)
        logger.info("device_updated", device_id=device_id)
        return device

    async def delete_device(self, db: AsyncSession, device_id: str) -> bool:
        """Delete a device by its device_id string."""
        device = await self.get_device(db, device_id)
        if not device:
            return False
        await db.delete(device)
        await db.flush()
        logger.info("device_deleted", device_id=device_id)
        return True

    # ── Device Commands ──────────────────────────────────────

    async def send_command(
        self,
        db: AsyncSession,
        device_id: str,
        action: str,
        value: int | float | str | None = None,
        source: str = "api",
    ) -> dict[str, Any]:
        """
        Send a command to a device via MQTT and log it.

        Returns a dict with command result information.
        """
        device = await self.get_device(db, device_id)
        if not device:
            return {
                "success": False,
                "error": f"Device '{device_id}' not found",
            }

        if not device.room:
            return {
                "success": False,
                "error": f"Device '{device_id}' has no associated room",
            }

        # Determine target state
        if action == CommandAction.TURN_ON.value:
            target_state = DeviceState.ON.value
        elif action == CommandAction.TURN_OFF.value:
            target_state = DeviceState.OFF.value
        elif action == CommandAction.TOGGLE.value:
            target_state = (
                DeviceState.OFF.value
                if device.state == DeviceState.ON.value
                else DeviceState.ON.value
            )
        elif action == CommandAction.SET_VALUE.value:
            target_state = device.state  # State unchanged, value is set
        elif action == CommandAction.GET_STATUS.value:
            return {
                "success": True,
                "device_id": device_id,
                "state": device.state,
                "is_online": device.is_online,
                "last_seen_at": str(device.last_seen_at) if device.last_seen_at else None,
            }
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

        # Build extra payload
        extra: dict[str, Any] = {}
        if value is not None:
            if action == CommandAction.SET_VALUE.value:
                extra["value"] = value

        # Publish via MQTT
        published = await mqtt_service.publish_command(
            room_slug=device.room.slug,
            device_id=device.device_id,
            state=target_state,
            extra_payload=extra if extra else None,
        )

        # Build command log
        payload_sent = {"state": target_state, "timestamp": int(time.time())}
        if extra:
            payload_sent.update(extra)

        status = "sent" if published else "failed"
        error_msg = None if published else "MQTT publish failed"

        command_log = CommandLog(
            device_id=device.device_id,
            action=action,
            payload=payload_sent,
            source=source,
            status=status,
            error_message=error_msg,
        )
        db.add(command_log)
        await db.flush()

        # Update DB state optimistically
        device.state = target_state
        if action == CommandAction.SET_VALUE.value and value is not None:
            try:
                num_val = float(value)
                if device.device_type == "ac":
                    device.temperature = num_val
                elif device.device_type == "light":
                    device.brightness = int(num_val)
            except (ValueError, TypeError):
                pass
        device.updated_at = datetime.now(timezone.utc)
        await db.flush()

        # Broadcast update to connected frontend WebSockets
        try:
            room_slug = device.room.slug if device.room else "unknown"
            extra_ws: dict[str, Any] = {}
            if device.brightness is not None:
                extra_ws["brightness"] = device.brightness
            if device.temperature is not None:
                extra_ws["temperature"] = device.temperature
            await ws_manager.broadcast_device_status(
                device_id=device.device_id,
                room_slug=room_slug,
                state=device.state,
                extra=extra_ws if extra_ws else None,
            )
        except Exception:
            pass

        logger.info(
            "device_command_sent",
            device_id=device.device_id,
            action=action,
            target_state=target_state,
            published=published,
        )

        return {
            "success": True,
            "device_id": device.device_id,
            "action": action,
            "payload_sent": payload_sent,
            "status": status,
            "message": f"Command '{action}' sent to {device.name}",
        }

    # ── Status Update (from MQTT) ────────────────────────────

    async def handle_status_update(
        self,
        db: AsyncSession,
        device_id: str,
        state: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """
        Process a device status update received from MQTT.

        Updates the device record and broadcasts via WebSocket.
        """
        device = await self.get_device(db, device_id)
        if not device:
            logger.warning("status_update_unknown_device", device_id=device_id)
            return

        device.state = state
        device.is_online = True
        device.last_seen_at = datetime.now(timezone.utc)

        if extra:
            if "brightness" in extra:
                device.brightness = extra["brightness"]
            if "temperature" in extra:
                device.temperature = extra["temperature"]
            if "humidity" in extra:
                device.humidity = extra["humidity"]

        device.updated_at = datetime.now(timezone.utc)
        await db.flush()

        # Broadcast to frontend via WebSocket
        room_slug = device.room.slug if device.room else "unknown"
        await ws_manager.broadcast_device_status(
            device_id=device_id,
            room_slug=room_slug,
            state=state,
            extra=extra,
        )

        logger.info(
            "device_status_updated",
            device_id=device_id,
            state=state,
        )

    # ── Telemetry ────────────────────────────────────────────

    async def save_telemetry(
        self,
        db: AsyncSession,
        device_id: str,
        temperature: float | None = None,
        humidity: float | None = None,
        power_watts: float | None = None,
        extra_data: dict | None = None,
    ) -> TelemetryLog:
        """Persist a telemetry reading and broadcast via WebSocket."""
        log = TelemetryLog(
            device_id=device_id,
            temperature=temperature,
            humidity=humidity,
            power_watts=power_watts,
            extra_data=extra_data,
        )
        db.add(log)
        await db.flush()

        # Update device's sensor fields
        stmt = (
            update(Device)
            .where(Device.device_id == device_id)
            .values(
                temperature=temperature,
                humidity=humidity,
                is_online=True,
                last_seen_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        await db.execute(stmt)

        # Broadcast to frontend
        await ws_manager.broadcast_telemetry(
            device_id=device_id,
            telemetry={
                "temperature": temperature,
                "humidity": humidity,
                "power_watts": power_watts,
                "recorded_at": log.recorded_at.isoformat(),
            },
        )

        return log

    async def get_telemetry(
        self,
        db: AsyncSession,
        device_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[TelemetryLog], int]:
        """Query telemetry logs with optional device filter."""
        query = select(TelemetryLog).order_by(TelemetryLog.recorded_at.desc())

        if device_id:
            query = query.where(TelemetryLog.device_id == device_id)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()

        query = query.offset(offset).limit(limit)
        result = await db.execute(query)
        logs = list(result.scalars().all())

        return logs, total

    # ── Command Logs ─────────────────────────────────────────

    async def get_command_logs(
        self,
        db: AsyncSession,
        device_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CommandLog], int]:
        """Query command logs with optional device filter."""
        query = select(CommandLog).order_by(CommandLog.executed_at.desc())

        if device_id:
            query = query.where(CommandLog.device_id == device_id)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()

        query = query.offset(offset).limit(limit)
        result = await db.execute(query)
        logs = list(result.scalars().all())

        return logs, total


# Module-level singleton
device_manager = DeviceManager()
