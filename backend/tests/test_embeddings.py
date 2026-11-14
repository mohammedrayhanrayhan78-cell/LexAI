"""Tests for EmbeddingService — Gemini REST calls are mocked via httpx."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import httpx

from app.core.embeddings import EmbeddingService, _apply_prefix


# ── Unit: prefix logic ────────────────────────────────────────────────────────

def test_prefix_query():
    assert _apply_prefix("hello", "retrieval_query").startswith("query: ")


def test_prefix_document():
    assert _apply_prefix("hello", "retrieval_document").startswith("passage: ")


def test_prefix_uppercase_query():
    assert _apply_prefix("hello", "RETRIEVAL_QUERY").startswith("query: ")


# ── Unit: single embed ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_embedding_success():
    fake_values = [0.1] * 768
    fake_response = MagicMock(spec=httpx.Response)
    fake_response.status_code = 200
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {"embedding": {"values": fake_values}}
    fake_response.headers = {}

    with patch("app.core.embeddings.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=fake_response)
        mock_client_cls.return_value = mock_client

        svc = EmbeddingService()
        result = await svc.get_embedding("some legal text", task_type="retrieval_document")

    assert len(result) == 768
    assert result[0] == pytest.approx(0.1)


@pytest.mark.asyncio
async def test_get_embedding_wrong_dim_raises():
    fake_values = [0.1] * 512  # wrong dimension
    fake_response = MagicMock(spec=httpx.Response)
    fake_response.status_code = 200
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {"embedding": {"values": fake_values}}
    fake_response.headers = {}

    with patch("app.core.embeddings.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=fake_response)
        mock_client_cls.return_value = mock_client

        svc = EmbeddingService()
        with pytest.raises(ValueError, match="Expected 768"):
            await svc.get_embedding("text")


# ── Unit: batch embed ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_embeddings_batch_two_texts():
    """Two texts → batch endpoint called once."""
    fake_embeddings = [{"values": [0.5] * 768}, {"values": [0.6] * 768}]
    fake_response = MagicMock(spec=httpx.Response)
    fake_response.status_code = 200
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {"embeddings": fake_embeddings}
    fake_response.headers = {}

    with patch("app.core.embeddings.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=fake_response)
        mock_client_cls.return_value = mock_client

        svc = EmbeddingService()
        results = await svc.get_embeddings_batch(["text one", "text two"])

    assert len(results) == 2
    assert len(results[0]) == 768


@pytest.mark.asyncio
async def test_get_embeddings_empty_list():
    svc = EmbeddingService()
    result = await svc.get_embeddings_batch([])
    assert result == []


# ── Unit: 429 retry ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retry_on_429():
    """Should retry on 429 and succeed on second attempt."""
    rate_limited = MagicMock(spec=httpx.Response)
    rate_limited.status_code = 429
    rate_limited.headers = {"Retry-After": "0"}
    rate_limited.raise_for_status = MagicMock()

    success = MagicMock(spec=httpx.Response)
    success.status_code = 200
    success.raise_for_status = MagicMock()
    success.json.return_value = {"embedding": {"values": [0.1] * 768}}
    success.headers = {}

    with (
        patch("app.core.embeddings.httpx.AsyncClient") as mock_client_cls,
        patch("app.core.embeddings.asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=[rate_limited, success])
        mock_client_cls.return_value = mock_client

        svc = EmbeddingService()
        result = await svc.get_embedding("text")

    assert len(result) == 768
