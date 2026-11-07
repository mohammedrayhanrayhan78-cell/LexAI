from __future__ import annotations

import logging
from typing import List

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_GEMINI_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"

_TASK_TYPE_MAP = {
    "retrieval_document": "RETRIEVAL_DOCUMENT",
    "retrieval_query": "RETRIEVAL_QUERY",
    "RETRIEVAL_DOCUMENT": "RETRIEVAL_DOCUMENT",
    "RETRIEVAL_QUERY": "RETRIEVAL_QUERY",
}


class EmbeddingService:
    def __init__(self) -> None:
        self.provider = settings.EMBEDDING_PROVIDER.lower()
        if self.provider != "gemini":
            raise ValueError(f"Unsupported embedding provider: {self.provider}")
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured for embeddings.")

    async def get_embedding(self, text: str, task_type: str = "retrieval_document") -> List[float]:
        try:
            return await self._gemini_embed(text, task_type)
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    async def _gemini_embed(self, text: str, task_type: str) -> List[float]:
        api_task = _TASK_TYPE_MAP.get(task_type, "RETRIEVAL_DOCUMENT")
        url = _GEMINI_EMBED_URL.format(model=settings.EMBEDDING_MODEL)
        payload = {
            "content": {"parts": [{"text": text}]},
            "taskType": api_task,
            "outputDimensionality": settings.EMBEDDING_DIMENSIONS,
        }
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": settings.GEMINI_API_KEY or "",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        values = data.get("embedding", {}).get("values")
        if not values:
            raise ValueError("Gemini embedContent returned no embedding values.")
        if len(values) != settings.EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Expected {settings.EMBEDDING_DIMENSIONS}-d embedding, got {len(values)}."
            )
        return values
