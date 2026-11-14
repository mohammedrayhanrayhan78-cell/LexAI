"""
Shared pytest fixtures for LexAI backend tests.
All external I/O (DB, Gemini, Groq) is mocked — no live keys required.
"""
from __future__ import annotations

import os
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# ── Set env vars BEFORE any app import so Settings() doesn't fail ──────────
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_that_is_long_enough_for_validation")
os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "test_refresh_key_that_is_long_enough_ok")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("GEMINI_API_KEY", "fake-gemini-key")
os.environ.setdefault("GROQ_API_KEY", "fake-groq-key")
os.environ.setdefault("POSTGRES_PASSWORD", "test")

from app.main import app  # noqa: E402  (must come after env setup)
from app.core.database import get_db  # noqa: E402
from app.api.deps import get_current_user  # noqa: E402
from app.models.user import User  # noqa: E402
from app.core.security import create_access_token, create_refresh_token  # noqa: E402


# ── Fake DB session ─────────────────────────────────────────────────────────
class FakeDB:
    """Minimal async SQLAlchemy session stub."""
    def __init__(self) -> None:
        self._store: dict = {}

    async def execute(self, *a, **kw):
        result = MagicMock()
        result.scalars.return_value.first.return_value = None
        result.scalars.return_value.all.return_value = []
        result.scalar.return_value = None
        return result

    def add(self, obj): pass
    async def commit(self): pass
    async def refresh(self, obj): pass
    async def delete(self, obj): pass
    async def close(self): pass


async def override_get_db() -> AsyncGenerator:
    yield FakeDB()


# ── Fake current user ───────────────────────────────────────────────────────
FAKE_USER_ID = uuid.uuid4()

def make_fake_user() -> User:
    u = MagicMock(spec=User)
    u.id = FAKE_USER_ID
    u.email = "test@lexai.dev"
    u.is_active = True
    u.full_name = "Test User"
    return u


def override_get_current_user() -> User:
    return make_fake_user()


# ── Apply overrides ─────────────────────────────────────────────────────────
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user


# ── Fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=True)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def access_token() -> str:
    return create_access_token(subject=FAKE_USER_ID)


@pytest.fixture
def auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def fake_user() -> User:
    return make_fake_user()
