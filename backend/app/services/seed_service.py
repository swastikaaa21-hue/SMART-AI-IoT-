"""
Seed service to populate default Smart Home rooms and devices.
"""

from __future__ import annotations

import uuid
from typing import Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room import Room
from app.models.device import Device
from app.core.logging import get_logger

logger = get_logger("seed_service")

DEFAULT_ROOMS_DATA: list[dict[str, Any]] = [
    {
        "name": "Kamar",
        "slug": "kamar",
        "room_type": "bedroom",
        "icon": "🛏️",
        "description": "Kamar Tidur Utama",
        "devices": [
            {
                "device_id": "dev-km-1",
                "name": "Lampu Kamar",
                "device_type": "light",
                "state": "off",
                "brightness": 80,
                "is_online": True,
                "description": "Lampu Plafon Kamar",
            },
            {
                "device_id": "dev-km-2",
                "name": "AC Kamar",
                "device_type": "ac",
                "state": "off",
                "temperature": 24.0,
                "is_online": True,
                "description": "Inverter AC Kamar",
            },
            {
                "device_id": "dev-km-3",
                "name": "Samsung TV",
                "device_type": "tv",
                "state": "off",
                "is_online": True,
                "description": "Smart TV Kamar 43 Inch",
                "extra_metadata": {"channel": 7, "volume": 18, "input": "HDMI 1"},
            },
            {
                "device_id": "dev-km-4",
                "name": "Smart Tirai",
                "device_type": "curtain",
                "state": "off",
                "is_online": True,
                "description": "Motorized Curtain Kamar",
                "extra_metadata": {"position": "Closed", "percent": 0},
            },
        ],
    },
    {
        "name": "Ruang Tamu",
        "slug": "ruang-tamu",
        "room_type": "living_room",
        "icon": "🛋️",
        "description": "Ruang Tamu & Keluarga",
        "devices": [
            {
                "device_id": "dev-rt-1",
                "name": "Lampu Utama",
                "device_type": "light",
                "state": "off",
                "brightness": 100,
                "is_online": True,
                "description": "Lampu Utama Ruang Tamu",
            },
            {
                "device_id": "dev-rt-2",
                "name": "Ambient Light",
                "device_type": "light",
                "state": "off",
                "brightness": 45,
                "is_online": True,
                "description": "RGB Light Strip TV",
            },
            {
                "device_id": "dev-rt-3",
                "name": "LG Smart TV",
                "device_type": "tv",
                "state": "off",
                "is_online": True,
                "description": "OLED 4K Living Room TV",
                "extra_metadata": {"channel": 12, "volume": 22, "input": "HDMI 2"},
            },
            {
                "device_id": "dev-rt-4",
                "name": "Sony Soundbar",
                "device_type": "speaker",
                "state": "off",
                "is_online": True,
                "description": "Dolby Atmos Soundbar",
                "extra_metadata": {"volume": 35, "playing": False},
            },
        ],
    },
    {
        "name": "Ruang Rapat",
        "slug": "ruang-rapat",
        "room_type": "office",
        "icon": "💼",
        "description": "Ruang Rapat & Kerja",
        "devices": [
            {
                "device_id": "dev-rr-1",
                "name": "Epson Projector",
                "device_type": "projector",
                "state": "off",
                "is_online": True,
                "description": "Laser Full HD Projector",
                "extra_metadata": {"input": "HDMI 1", "ecoMode": False},
            },
            {
                "device_id": "dev-rr-2",
                "name": "Daikin AC Rapat",
                "device_type": "ac",
                "state": "off",
                "temperature": 23.0,
                "is_online": True,
                "description": "Daikin Inverter Meeting Room",
            },
            {
                "device_id": "dev-rr-3",
                "name": "Lampu Rapat Panel",
                "device_type": "light",
                "state": "off",
                "brightness": 90,
                "is_online": True,
                "description": "Panel LED Lighting",
            },
        ],
    },
    {
        "name": "Studio",
        "slug": "studio",
        "room_type": "studio",
        "icon": "🎨",
        "description": "Studio Kreatif",
        "devices": [
            {
                "device_id": "dev-st-1",
                "name": "Sharp AC",
                "device_type": "ac",
                "state": "off",
                "temperature": 24.0,
                "is_online": True,
                "description": "Plasmacluster AC Studio",
            },
            {
                "device_id": "dev-st-2",
                "name": "Lampu Studio",
                "device_type": "light",
                "state": "off",
                "brightness": 100,
                "is_online": True,
                "description": "Daylight 5600K Studio Lamp",
            },
        ],
    },
]


async def seed_user_default_data(db: AsyncSession, user_id: uuid.UUID, reset: bool = False) -> tuple[int, int]:
    """
    Seed initial default rooms and devices for a user.
    If reset is True, clears existing rooms/devices for this user first.
    """
    if reset:
        existing_rooms = await db.execute(select(Room).where(Room.owner_id == user_id))
        for r in existing_rooms.scalars().all():
            await db.delete(r)
        await db.flush()

    rooms_count = 0
    devices_count = 0

    for r_data in DEFAULT_ROOMS_DATA:
        # Check if room already exists for this user or slug
        room_res = await db.execute(select(Room).where(Room.slug == r_data["slug"]))
        room = room_res.scalar_one_or_none()

        if not room:
            room = Room(
                name=r_data["name"],
                slug=r_data["slug"],
                room_type=r_data["room_type"],
                icon=r_data.get("icon"),
                description=r_data.get("description"),
                owner_id=user_id,
            )
            db.add(room)
            await db.flush()
            await db.refresh(room)
            rooms_count += 1
        elif room.owner_id != user_id:
            # Reassign owner if needed
            room.owner_id = user_id
            await db.flush()

        for d_data in r_data.get("devices", []):
            dev_res = await db.execute(select(Device).where(Device.device_id == d_data["device_id"]))
            device = dev_res.scalar_one_or_none()

            if not device:
                device = Device(
                    device_id=d_data["device_id"],
                    name=d_data["name"],
                    device_type=d_data["device_type"],
                    room_id=room.id,
                    state=d_data.get("state", "off"),
                    brightness=d_data.get("brightness"),
                    temperature=d_data.get("temperature"),
                    humidity=d_data.get("humidity", 65.0),
                    is_online=d_data.get("is_online", True),
                    description=d_data.get("description"),
                    extra_metadata=d_data.get("extra_metadata", {}),
                )
                db.add(device)
                await db.flush()
                devices_count += 1
            else:
                # Update room relation if needed
                if device.room_id != room.id:
                    device.room_id = room.id
                    await db.flush()

    logger.info("seed_user_data_complete", user_id=str(user_id), rooms=rooms_count, devices=devices_count)
    return rooms_count, devices_count
