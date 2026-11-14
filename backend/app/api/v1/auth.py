from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.config import settings
from app.core.database import get_db
from app.crud.crud_user import user_crud
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    RefreshTokenRequest,
    UserResponse,
)
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.api.deps import get_current_user, ACCESS_COOKIE, REFRESH_COOKIE
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

# The refresh cookie is only sent to auth endpoints, so it is never attached
# to ordinary API calls.
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _cookie_secure() -> bool:
    return settings.ENVIRONMENT.lower() == "production"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Store both tokens in HttpOnly cookies so page JavaScript cannot read them."""
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=ACCESS_COOKIE, path="/", secure=_cookie_secure(), httponly=True, samesite="lax")
    response.delete_cookie(
        key=REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, secure=_cookie_secure(), httponly=True, samesite="lax"
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)) -> User:
    existing_user = await user_crud.get_by_email(db, email=user_in.email)
    if existing_user:
        logger.warning(f"Registration attempt with existing email: {user_in.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )
    user = await user_crud.create(db, obj_in=user_in)
    logger.info(f"User registered successfully: {user.email}")
    return user


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    credentials: UserLogin, response: Response, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    user = await user_crud.get_by_email(db, email=credentials.email)
    if not user or not verify_password(credentials.password, user.hashed_password):
        logger.warning(f"Failed login attempt for email: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    _set_auth_cookies(response, access_token, refresh_token)
    logger.info(f"User logged in successfully: {user.email}")
    return {"message": "Logged in."}


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_token(
    request: Request,
    response: Response,
    body: Optional[RefreshTokenRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    # Prefer the HttpOnly cookie; fall back to a body token for non-browser clients.
    raw_refresh = request.cookies.get(REFRESH_COOKIE) or (body.refresh_token if body else None)
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    payload = decode_token(raw_refresh, refresh=True)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload.",
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier.",
        )

    user = await user_crud.get_by_id(db, user_id=user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )

    new_access_token = create_access_token(subject=user.id)
    new_refresh_token = create_refresh_token(subject=user.id)
    _set_auth_cookies(response, new_access_token, new_refresh_token)
    return {"message": "Refreshed."}


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response) -> dict[str, str]:
    # No auth required: logging out must work even when the access token has expired.
    _clear_auth_cookies(response)
    return {"message": "Successfully logged out."}


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
