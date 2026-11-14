"""Tests for /api/v1/auth endpoints."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.security import create_access_token, create_refresh_token, hash_password
from app.models.user import User


def _make_db_user(email: str = "user@lexai.dev") -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.email = email
    u.hashed_password = hash_password("Password123!")
    u.is_active = True
    u.full_name = "Test User"
    return u


# ── Registration ─────────────────────────────────────────────────────────────

def test_register_new_user(client):
    with patch("app.api.v1.auth.user_crud") as mock_crud:
        mock_crud.get_by_email = AsyncMock(return_value=None)
        created = _make_db_user("new@lexai.dev")
        mock_crud.create = AsyncMock(return_value=created)

        resp = client.post("/api/v1/auth/register", json={
            "email": "new@lexai.dev",
            "password": "Password123!",
            "full_name": "New User",
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@lexai.dev"


def test_register_duplicate_email(client):
    with patch("app.api.v1.auth.user_crud") as mock_crud:
        mock_crud.get_by_email = AsyncMock(return_value=_make_db_user())

        resp = client.post("/api/v1/auth/register", json={
            "email": "user@lexai.dev",
            "password": "Password123!",
            "full_name": "Dup User",
        })
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_success(client):
    db_user = _make_db_user()
    with patch("app.api.v1.auth.user_crud") as mock_crud:
        mock_crud.get_by_email = AsyncMock(return_value=db_user)

        resp = client.post("/api/v1/auth/login", json={
            "email": db_user.email,
            "password": "Password123!",
        })
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client):
    db_user = _make_db_user()
    with patch("app.api.v1.auth.user_crud") as mock_crud:
        mock_crud.get_by_email = AsyncMock(return_value=db_user)

        resp = client.post("/api/v1/auth/login", json={
            "email": db_user.email,
            "password": "WrongPass!",
        })
    assert resp.status_code == 401


def test_login_unknown_user(client):
    with patch("app.api.v1.auth.user_crud") as mock_crud:
        mock_crud.get_by_email = AsyncMock(return_value=None)

        resp = client.post("/api/v1/auth/login", json={
            "email": "ghost@lexai.dev",
            "password": "whatever",
        })
    assert resp.status_code == 401


def test_login_inactive_user(client):
    db_user = _make_db_user()
    db_user.is_active = False
    with patch("app.api.v1.auth.user_crud") as mock_crud:
        mock_crud.get_by_email = AsyncMock(return_value=db_user)

        resp = client.post("/api/v1/auth/login", json={
            "email": db_user.email,
            "password": "Password123!",
        })
    assert resp.status_code == 403


# ── Token refresh ─────────────────────────────────────────────────────────────

def test_refresh_token_success(client):
    db_user = _make_db_user()
    refresh_tok = create_refresh_token(subject=db_user.id)
    with patch("app.api.v1.auth.user_crud") as mock_crud:
        mock_crud.get_by_id = AsyncMock(return_value=db_user)

        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_tok})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_refresh_token_invalid(client):
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "not.a.token"})
    assert resp.status_code == 401


# ── Protected route: /me ──────────────────────────────────────────────────────

def test_get_me(client, auth_headers, fake_user):
    # get_current_user is already overridden in conftest
    resp = client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == fake_user.email


def test_get_me_no_token(client):
    # Remove the dependency override temporarily
    from app.main import app as _app
    from app.api.deps import get_current_user as _dep
    _app.dependency_overrides.pop(_dep, None)
    try:
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401
    finally:
        from tests.conftest import override_get_current_user
        _app.dependency_overrides[_dep] = override_get_current_user
