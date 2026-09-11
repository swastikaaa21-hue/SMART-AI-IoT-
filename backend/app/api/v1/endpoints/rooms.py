"""
Room management endpoints.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.db.session import get_db
from app.middleware.auth import get_current_user
from app.models.room import Room
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.room import RoomCreate, RoomResponse, RoomUpdate, RoomWithDevices
from app.utils.exceptions import AlreadyExistsError, NotFoundError

router = APIRouter()


@router.get("", response_model=PaginatedResponse[RoomResponse])
async def list_rooms(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all rooms belonging to the current user."""
    base_query = select(Room).where(Room.owner_id == user.id)

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    # If user has 0 rooms, auto-seed default rooms
    if total == 0:
        from app.services.seed_service import seed_user_default_data
        await seed_user_default_data(db, user.id, reset=False)
        count_result = await db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar_one()

    result = await db.execute(
        base_query
        .options(selectinload(Room.devices))
        .order_by(Room.created_at)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rooms = list(result.scalars().all())

    items = []
    for r in rooms:
        data = RoomResponse.model_validate(r)
        data.total_devices_count = len(r.devices)
        data.active_devices_count = sum(1 for d in r.devices if d.state == "on")
        items.append(data)

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{room_id}", response_model=RoomWithDevices)
async def get_room(
    room_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single room with its devices."""
    result = await db.execute(
        select(Room)
        .where(Room.id == room_id, Room.owner_id == user.id)
        .options(selectinload(Room.devices))
    )
    room = result.scalar_one_or_none()
    if not room:
        raise NotFoundError("Room", str(room_id))

    data = RoomWithDevices.model_validate(room)
    data.total_devices_count = len(room.devices)
    data.active_devices_count = sum(1 for d in room.devices if d.state == "on")
    return data


@router.post("", response_model=RoomResponse, status_code=201)
async def create_room(
    body: RoomCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new room."""
    # Check for duplicate slug
    existing = await db.execute(select(Room).where(Room.slug == body.slug))
    if existing.scalar_one_or_none():
        raise AlreadyExistsError("Room", body.slug)

    room = Room(
        name=body.name,
        slug=body.slug,
        room_type=body.room_type,
        description=body.description,
        icon=body.icon,
        owner_id=user.id,
    )
    db.add(room)
    await db.flush()
    await db.refresh(room)
    return room


@router.patch("/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: uuid.UUID,
    body: RoomUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing room."""
    result = await db.execute(
        select(Room).where(Room.id == room_id, Room.owner_id == user.id)
    )
    room = result.scalar_one_or_none()
    if not room:
        raise NotFoundError("Room", str(room_id))

    if body.name is not None:
        room.name = body.name
    if body.room_type is not None:
        room.room_type = body.room_type
    if body.description is not None:
        room.description = body.description
    if body.icon is not None:
        room.icon = body.icon

    await db.flush()
    await db.refresh(room)
    return room


@router.delete("/{room_id}", response_model=SuccessResponse)
async def delete_room(
    room_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a room and all its associated devices."""
    result = await db.execute(
        select(Room).where(Room.id == room_id, Room.owner_id == user.id)
    )
    room = result.scalar_one_or_none()
    if not room:
        raise NotFoundError("Room", str(room_id))

    await db.delete(room)
    await db.flush()
    return SuccessResponse(message=f"Room '{room.name}' deleted successfully")
