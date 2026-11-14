"""Tests for GeminiProvider (httpx REST rewrite)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from app.core.llm.gemini_provider import GeminiProvider, _merge_messages


# ── Unit: message merging ─────────────────────────────────────────────────────

def test_merge_extracts_system():
    msgs = [
        {"role": "system", "content": "Be helpful."},
        {"role": "user", "content": "Hello"},
    ]
    system, contents = _merge_messages(msgs)
    assert system == "Be helpful."
    assert contents[0]["role"] == "user"


def test_merge_consecutive_same_role():
    msgs = [
        {"role": "user", "content": "first"},
        {"role": "user", "content": "second"},
    ]
    _, contents = _merge_messages(msgs)
    assert len(contents) == 1
    assert len(contents[0]["parts"]) == 2


def test_merge_starts_with_model_inserts_empty_user():
    msgs = [{"role": "assistant", "content": "hi"}]
    _, contents = _merge_messages(msgs)
    assert contents[0]["role"] == "user"


def test_merge_no_system():
    msgs = [{"role": "user", "content": "query"}]
    system, contents = _merge_messages(msgs)
    assert system is None
    assert contents[0]["role"] == "user"


# ── Integration: generate ─────────────────────────────────────────────────────

def _make_gemini_response(text: str) -> dict:
    return {
        "candidates": [
            {"content": {"parts": [{"text": text}]}}
        ]
    }


@pytest.mark.asyncio
async def test_generate_success():
    fake_resp = MagicMock(spec=httpx.Response)
    fake_resp.status_code = 200
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json.return_value = _make_gemini_response("Here is the legal answer.")

    with patch("app.core.llm.gemini_provider.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=fake_resp)
        mock_cls.return_value = mock_client

        provider = GeminiProvider()
        result = await provider.generate([{"role": "user", "content": "What is IPC section 302?"}])

    assert "legal answer" in result


@pytest.mark.asyncio
async def test_generate_empty_response_raises():
    fake_resp = MagicMock(spec=httpx.Response)
    fake_resp.status_code = 200
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json.return_value = {"candidates": [{"content": {"parts": []}}]}

    with patch("app.core.llm.gemini_provider.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=fake_resp)
        mock_cls.return_value = mock_client

        provider = GeminiProvider()
        with pytest.raises(ValueError, match="empty text"):
            await provider.generate([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_generate_skips_thought_parts():
    """Parts with thought=True should not appear in output."""
    fake_resp = MagicMock(spec=httpx.Response)
    fake_resp.status_code = 200
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [
                    {"text": "thinking...", "thought": True},
                    {"text": "real answer"},
                ]
            }
        }]
    }

    with patch("app.core.llm.gemini_provider.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=fake_resp)
        mock_cls.return_value = mock_client

        provider = GeminiProvider()
        result = await provider.generate([{"role": "user", "content": "query"}])

    assert result == "real answer"
    assert "thinking" not in result


@pytest.mark.asyncio
async def test_generate_with_image():
    fake_resp = MagicMock(spec=httpx.Response)
    fake_resp.status_code = 200
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json.return_value = _make_gemini_response("Image shows a court order.")

    with patch("app.core.llm.gemini_provider.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=fake_resp)
        mock_cls.return_value = mock_client

        provider = GeminiProvider()
        result = await provider.generate_with_image(
            [{"role": "user", "content": "What does this say?"}],
            image_bytes=b"fake-image-bytes",
        )

    assert "court order" in result
    # Verify inline_data was included in the payload
    call_kwargs = mock_client.post.call_args
    payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs[0][1]
    last_parts = payload["contents"][-1]["parts"]
    assert any("inline_data" in p for p in last_parts)
