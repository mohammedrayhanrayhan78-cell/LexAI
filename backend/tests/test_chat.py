"""Tests for /api/v1/chat endpoints."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_conv(conv_id=None, title="Test Conv"):
    c = MagicMock()
    c.id = conv_id or uuid.uuid4()
    c.title = title
    c.user_id = uuid.uuid4()
    return c


def _make_msg(role="user", content="hello"):
    m = MagicMock()
    m.id = uuid.uuid4()
    m.role = role
    m.content = content
    m.conversation_id = uuid.uuid4()
    return m


# ── Conversations ─────────────────────────────────────────────────────────────

def test_create_conversation(client, auth_headers):
    fake_conv = _make_conv()
    with patch("app.api.v1.chat.chat_crud") as mock_crud:
        mock_crud.create_conversation = AsyncMock(return_value=fake_conv)
        resp = client.post(
            "/api/v1/chat/conversations",
            headers=auth_headers,
            json={"title": "Test Conv"},
        )
    assert resp.status_code == 201


def test_list_conversations_empty(client, auth_headers):
    with patch("app.api.v1.chat.chat_crud") as mock_crud:
        mock_crud.get_conversations_by_user = AsyncMock(return_value=[])
        resp = client.get("/api/v1/chat/conversations", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_conversations_requires_auth(client):
    from app.main import app as _app
    from app.api.deps import get_current_user as _dep
    _app.dependency_overrides.pop(_dep, None)
    try:
        resp = client.get("/api/v1/chat/conversations")
        assert resp.status_code == 401
    finally:
        from tests.conftest import override_get_current_user
        _app.dependency_overrides[_dep] = override_get_current_user


# ── Messages ──────────────────────────────────────────────────────────────────

def test_get_messages_conversation_not_found(client, auth_headers):
    conv_id = uuid.uuid4()
    with patch("app.api.v1.chat.chat_crud") as mock_crud:
        mock_crud.get_conversation_by_id = AsyncMock(return_value=None)
        resp = client.get(f"/api/v1/chat/conversations/{conv_id}/messages", headers=auth_headers)
    assert resp.status_code == 404


def test_get_messages_success(client, auth_headers):
    conv = _make_conv()
    msgs = [_make_msg("user", "hi"), _make_msg("assistant", "Hello")]
    with patch("app.api.v1.chat.chat_crud") as mock_crud:
        mock_crud.get_conversation_by_id = AsyncMock(return_value=conv)
        mock_crud.get_messages_by_conversation = AsyncMock(return_value=msgs)
        resp = client.get(
            f"/api/v1/chat/conversations/{conv.id}/messages",
            headers=auth_headers,
        )
    assert resp.status_code == 200


def test_post_message_success(client, auth_headers):
    conv = _make_conv()
    user_msg = _make_msg("user", "What is IPC 302?")
    asst_msg = _make_msg("assistant", "IPC Section 302 deals with murder.")

    with (
        patch("app.api.v1.chat.chat_crud") as mock_crud,
        patch("app.api.v1.chat.LegalAgentGraph") as mock_graph_cls,
    ):
        mock_crud.get_conversation_by_id = AsyncMock(return_value=conv)
        mock_crud.get_messages_by_conversation = AsyncMock(return_value=[user_msg])
        mock_crud.create_message = AsyncMock(side_effect=[user_msg, asst_msg])

        mock_graph = MagicMock()
        mock_graph.run = AsyncMock(return_value="IPC Section 302 deals with murder.")
        mock_graph_cls.return_value = mock_graph

        resp = client.post(
            f"/api/v1/chat/conversations/{conv.id}/messages",
            headers=auth_headers,
            data={"content": "What is IPC 302?"},
        )
    assert resp.status_code == 201


def test_post_message_conv_not_found(client, auth_headers):
    conv_id = uuid.uuid4()
    with patch("app.api.v1.chat.chat_crud") as mock_crud:
        mock_crud.get_conversation_by_id = AsyncMock(return_value=None)
        resp = client.post(
            f"/api/v1/chat/conversations/{conv_id}/messages",
            headers=auth_headers,
            data={"content": "hi"},
        )
    assert resp.status_code == 404


def test_post_message_bad_image_type(client, auth_headers):
    import io
    conv = _make_conv()
    with patch("app.api.v1.chat.chat_crud") as mock_crud:
        mock_crud.get_conversation_by_id = AsyncMock(return_value=conv)
        resp = client.post(
            f"/api/v1/chat/conversations/{conv.id}/messages",
            headers=auth_headers,
            data={"content": "look at this"},
            files={"image": ("file.gif", io.BytesIO(b"gif data"), "image/gif")},
        )
    assert resp.status_code == 400
    assert "Unsupported image type" in resp.json()["detail"]
