from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any, Dict, List

import httpx

from app.core.llm.base import BaseLLMProvider
from app.core.config import settings

logger = logging.getLogger(__name__)

_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

_SYSTEM_PROMPT = (
    "You are LexAI, an expert AI Legal Assistant specialising in Indian law and judicial "
    "procedures. Answer accurately, cite relevant statutes or case law where appropriate, "
    "and always clarify that your responses are for research purposes and not formal legal advice."
)


def _merge_messages(messages: List[Dict[str, str]]) -> tuple[str | None, List[Dict]]:
    """
    Split out system messages and merge consecutive same-role turns.
    Gemini REST requires strict user/model alternation and no system role.
    Returns (system_text_or_None, gemini_contents_list).
    """
    system_parts: List[str] = []
    rest: List[Dict[str, str]] = []
    for m in messages:
        if m["role"] == "system":
            system_parts.append(m["content"])
        else:
            rest.append(m)

    system_text = "\n\n".join(system_parts) if system_parts else None

    # Map roles and merge consecutive identical roles
    contents: List[Dict] = []
    for m in rest:
        role = "user" if m["role"] == "user" else "model"
        if contents and contents[-1]["role"] == role:
            contents[-1]["parts"].append({"text": m["content"]})
        else:
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

    # Gemini must start with user turn
    if contents and contents[0]["role"] == "model":
        contents.insert(0, {"role": "user", "parts": [{"text": ""}]})

    return system_text, contents


class GeminiProvider(BaseLLMProvider):
    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured.")
        self.model_name = settings.GEMINI_MODEL
        self._headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": settings.GEMINI_API_KEY,
        }

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        extra_system: str | None = None,
    ) -> Dict:
        system_text, contents = _merge_messages(messages)
        combined_system = "\n\n".join(
            filter(None, [_SYSTEM_PROMPT, system_text, extra_system])
        )
        payload: Dict[str, Any] = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": combined_system}]},
            "generationConfig": {
                "thinkingConfig": {"thinkingBudget": 0},  # minimal / no thinking
            },
        }
        return payload

    async def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        url = _GENERATE_URL.format(model=self.model_name)
        payload = self._build_payload(messages)
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS + 10) as client:
            resp = await asyncio.wait_for(
                client.post(url, json=payload, headers=self._headers),
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            return self._extract_text(resp.json())

    async def generate_with_image(
        self, messages: List[Dict[str, str]], image_bytes: bytes, **kwargs: Any
    ) -> str:
        """Inject image as inline_data into the last user turn."""
        system_text, contents = _merge_messages(messages)
        combined_system = "\n\n".join(filter(None, [_SYSTEM_PROMPT, system_text]))

        b64 = base64.b64encode(image_bytes).decode("utf-8")
        image_part = {"inline_data": {"mime_type": "image/jpeg", "data": b64}}

        # Append image part to last user turn, or create one
        if contents and contents[-1]["role"] == "user":
            contents[-1]["parts"].append(image_part)
        else:
            contents.append({"role": "user", "parts": [image_part]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": combined_system}]},
            "generationConfig": {"thinkingConfig": {"thinkingBudget": 0}},
        }
        url = _GENERATE_URL.format(model=self.model_name)
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS + 10) as client:
            resp = await asyncio.wait_for(
                client.post(url, json=payload, headers=self._headers),
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            return self._extract_text(resp.json())

    @staticmethod
    def _extract_text(data: Dict) -> str:
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini returned no candidates.")
        parts = candidates[0].get("content", {}).get("parts", [])
        # Skip thought parts (thinkingContent)
        texts = [p["text"] for p in parts if "text" in p and not p.get("thought")]
        text = "".join(texts).strip()
        if not text:
            raise ValueError("Gemini returned empty text content.")
        return text
