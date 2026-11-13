from __future__ import annotations

import asyncio
import logging
import time
from typing import List

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_BATCH_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"
)
_SINGLE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"
)
_MAX_BATCH = 100
_MAX_RETRIES = 4


def _apply_prefix(text: str, task_type: str) -> str:
    """gemini-embedding-2 uses text prefixes instead of taskType field."""
    if task_type in ("retrieval_query", "RETRIEVAL_QUERY"):
        return f"query: {text}"
    # retrieval_document or anything else → document prefix
    return f"passage: {text}"


async def _post_with_backoff(client: httpx.AsyncClient, url: str, payload: dict) -> dict:
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": settings.GEMINI_API_KEY or "",
    }
    delay = 1.0
    for attempt in range(_MAX_RETRIES):
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 429 or resp.status_code >= 500:
            retry_after = float(resp.headers.get("Retry-After", delay))
            logger.warning(
                "Gemini embed HTTP %s on attempt %d; retrying in %.1fs",
                resp.status_code, attempt + 1, retry_after,
            )
            await asyncio.sleep(retry_after)
            delay = min(delay * 2, 60.0)
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return {}  # unreachable


class EmbeddingService:
    def __init__(self) -> None:
        provider = settings.EMBEDDING_PROVIDER.lower()
        if provider != "gemini":
            raise ValueError(f"Unsupported embedding provider: {provider}")
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured for embeddings.")

    async def get_embedding(self, text: str, task_type: str = "retrieval_document") -> List[float]:
        """Embed a single text string."""
        results = await self.get_embeddings_batch([text], task_type=task_type)
        return results[0]

    async def get_embeddings_batch(
        self, texts: List[str], task_type: str = "retrieval_document"
    ) -> List[List[float]]:
        """Embed a list of texts in batches of up to 100."""
        if not texts:
            return []
        all_embeddings: List[List[float]] = []
        model = settings.EMBEDDING_MODEL
        async with httpx.AsyncClient(timeout=120.0) as client:
            for i in range(0, len(texts), _MAX_BATCH):
                batch = texts[i : i + _MAX_BATCH]
                prefixed = [_apply_prefix(t, task_type) for t in batch]
                if len(prefixed) == 1:
                    # Use single-embed endpoint (simpler response shape)
                    url = _SINGLE_URL.format(model=model)
                    payload = {
                        "model": f"models/{model}",
                        "content": {"parts": [{"text": prefixed[0]}]},
                        "outputDimensionality": settings.EMBEDDING_DIMENSIONS,
                    }
                    data = await _post_with_backoff(client, url, payload)
                    values = data.get("embedding", {}).get("values")
                    if not values:
                        raise ValueError("Gemini embedContent returned no values.")
                    self._validate_dim(values)
                    all_embeddings.append(values)
                else:
                    url = _BATCH_URL.format(model=model)
                    payload = {
                        "model": f"models/{model}",
                        "requests": [
                            {
                                "model": f"models/{model}",
                                "content": {"parts": [{"text": t}]},
                                "outputDimensionality": settings.EMBEDDING_DIMENSIONS,
                            }
                            for t in prefixed
                        ],
                    }
                    data = await _post_with_backoff(client, url, payload)
                    embeddings_list = data.get("embeddings", [])
                    if len(embeddings_list) != len(batch):
                        raise ValueError(
                            f"Batch embed: expected {len(batch)} results, got {len(embeddings_list)}."
                        )
                    for item in embeddings_list:
                        values = item.get("values")
                        if not values:
                            raise ValueError("Gemini batchEmbedContents returned empty values.")
                        self._validate_dim(values)
                        all_embeddings.append(values)
        return all_embeddings

    def _validate_dim(self, values: List[float]) -> None:
        if len(values) != settings.EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Expected {settings.EMBEDDING_DIMENSIONS}-d embedding, got {len(values)}."
            )
