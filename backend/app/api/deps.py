from __future__ import annotations

import uuid
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import get_db
from app.core.security import decode_token
from app.crud.crud_user import user_crud
from app.models.user import User

logger = logging.getLogger(__name__)

# Cookie names used by the browser session. The access token is read from
# the cookie for the web app; an Authorization header is still accepted for
# API clients and tests.
ACCESS_COOKIE = "lexai_access"
REFRESH_COOKIE = "lexai_refresh"


def _extract_access_token(request: Request) -> str | None:
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip() or None
    return request.cookies.get(ACCESS_COOKIE)


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    token = _extract_access_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token, refresh=False)
    if payload is None:
        raise credentials_exception
    
    token_type = payload.get("type")
    if token_type != "access":
        raise credentials_exception

    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    user = await user_crud.get_by_id(db, user_id=user_id)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return user


async def get_current_active_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user