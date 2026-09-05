"""
Authentication dependency for FastAPI.

Extracts and validates JWT tokens from the Authorization header.
"""

from __future__ import annotations

import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.utils.exceptions import UnauthorizedError

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=True,
)

oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency that extracts the current user from the JWT token.

    Usage::

        @router.get("/me")
        async def me(user: User = Depends(get_current_user)):
            return user
    """
    try:
        payload = decode_token(token)
    except JWTError:
        raise UnauthorizedError("Invalid or expired token")

    token_type = payload.get("type")
    if token_type != "access":
        raise UnauthorizedError("Invalid token type")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedError("Token missing subject claim")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedError("Invalid user ID in token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedError("User not found")

    if not user.is_active:
        raise UnauthorizedError("User account is deactivated")

    return user


async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Optional authentication dependency.

    Returns the user if a valid token is present, or None otherwise.
    """
    if not token:
        return None

    try:
        return await get_current_user(token=token, db=db)
    except UnauthorizedError:
        return None


async def get_superuser(
    user: User = Depends(get_current_user),
) -> User:
    """Dependency that requires superuser privileges."""
    if not user.is_superuser:
        from app.utils.exceptions import ForbiddenError
        raise ForbiddenError("Superuser privileges required")
    return user
