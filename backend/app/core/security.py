from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, HashingError
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)
pwd_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    try:
        return pwd_hasher.hash(password)
    except HashingError as e:
        logger.error(f"Password hashing failed: {e}")
        raise ValueError("Password hashing failed.")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_hasher.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def create_access_token(subject: Union[str, Any], expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any], expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str, refresh: bool = False) -> dict[str, Any] | None:
    secret = settings.JWT_REFRESH_SECRET_KEY if refresh else settings.JWT_SECRET_KEY
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except Exception as e:
        logger.error(f"Token decoding failed: {e}")
        return None