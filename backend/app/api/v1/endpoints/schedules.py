"""Schedule/Routine endpoints."""

import uuid
from datetime import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.schedule import Schedule
from app.models.room import Room
from app.models.device import Device
from app.schemas.schedule import ScheduleCreate, ScheduleResponse, ScheduleUpdate

router = APIRouter()


@router.post("", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    schedule_in: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create new schedule/routine."""
    # Verify room and device exist and belong to user
    room_result = await db.execute(select(Room).where(Room.id == schedule_in.room_id, Room.owner_id == current_user.id))
    room = room_result.scalar_one_or_none()
    if not room:
        raise HTTPException(404, "Room not found")

    device_result = await db.execute(select(Device).where(Device.device_id == schedule_in.device_id, Device.room_id == room.id))
    device = device_result.scalar_one_or_none()
    if not device:
        raise HTTPException(404, "Device not found")

    schedule = Schedule(
        id=str(uuid.uuid4()),
        name=schedule_in.name,
        room_id=str(schedule_in.room_id),
        device_id=schedule_in.device_id,
        action=schedule_in.action,
        start_time=time.fromisoformat(schedule_in.start_time),
        end_time=time.fromisoformat(schedule_in.end_time) if schedule_in.end_time else None,
        days=schedule_in.days,
        parameters=schedule_in.parameters,
        user_id=str(current_user.id),
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        room_id=schedule.room_id,
        device_id=schedule.device_id,
        action=schedule.action,
        start_time=schedule.start_time.strftime("%H:%M"),
        end_time=schedule.end_time.strftime("%H:%M") if schedule.end_time else None,
        is_active=schedule.is_active,
        days=schedule.days,
        parameters=schedule.parameters,
        user_id=schedule.user_id,
        room_name=room.name,
        device_name=device.name,
    )


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all schedules for current user."""
    result = await db.execute(select(Schedule).where(Schedule.user_id == str(current_user.id)))
    schedules = result.scalars().all()

    responses = []
    for schedule in schedules:
        room_result = await db.execute(select(Room).where(Room.id == schedule.room_id))
        room = room_result.scalar_one_or_none()
        device_result = await db.execute(select(Device).where(Device.device_id == schedule.device_id))
        device = device_result.scalar_one_or_none()

        responses.append(ScheduleResponse(
            id=schedule.id,
            name=schedule.name,
            room_id=schedule.room_id,
            device_id=schedule.device_id,
            action=schedule.action,
            start_time=schedule.start_time.strftime("%H:%M"),
            end_time=schedule.end_time.strftime("%H:%M") if schedule.end_time else None,
            is_active=schedule.is_active,
            days=schedule.days,
            parameters=schedule.parameters,
            user_id=schedule.user_id,
            room_name=room.name if room else None,
            device_name=device.name if device else None,
        ))

    return responses


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get schedule detail."""
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id, Schedule.user_id == str(current_user.id)))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(404, "Schedule not found")

    room_result = await db.execute(select(Room).where(Room.id == schedule.room_id))
    room = room_result.scalar_one_or_none()
    device_result = await db.execute(select(Device).where(Device.device_id == schedule.device_id))
    device = device_result.scalar_one_or_none()

    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        room_id=schedule.room_id,
        device_id=schedule.device_id,
        action=schedule.action,
        start_time=schedule.start_time.strftime("%H:%M"),
        end_time=schedule.end_time.strftime("%H:%M") if schedule.end_time else None,
        is_active=schedule.is_active,
        days=schedule.days,
        parameters=schedule.parameters,
        user_id=schedule.user_id,
        room_name=room.name if room else None,
        device_name=device.name if device else None,
    )


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    schedule_in: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update schedule."""
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id, Schedule.user_id == str(current_user.id)))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(404, "Schedule not found")

    if schedule_in.name is not None:
        schedule.name = schedule_in.name
    if schedule_in.action is not None:
        schedule.action = schedule_in.action
    if schedule_in.start_time is not None:
        schedule.start_time = time.fromisoformat(schedule_in.start_time)
    if schedule_in.end_time is not None:
        schedule.end_time = time.fromisoformat(schedule_in.end_time)
    if schedule_in.is_active is not None:
        schedule.is_active = schedule_in.is_active
    if schedule_in.days is not None:
        schedule.days = schedule_in.days
    if schedule_in.parameters is not None:
        schedule.parameters = schedule_in.parameters

    await db.commit()
    await db.refresh(schedule)

    room_result = await db.execute(select(Room).where(Room.id == schedule.room_id))
    room = room_result.scalar_one_or_none()
    device_result = await db.execute(select(Device).where(Device.device_id == schedule.device_id))
    device = device_result.scalar_one_or_none()

    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        room_id=schedule.room_id,
        device_id=schedule.device_id,
        action=schedule.action,
        start_time=schedule.start_time.strftime("%H:%M"),
        end_time=schedule.end_time.strftime("%H:%M") if schedule.end_time else None,
        is_active=schedule.is_active,
        days=schedule.days,
        parameters=schedule.parameters,
        user_id=schedule.user_id,
        room_name=room.name if room else None,
        device_name=device.name if device else None,
    )


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete schedule."""
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id, Schedule.user_id == str(current_user.id)))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(404, "Schedule not found")

    await db.delete(schedule)
    await db.commit()
