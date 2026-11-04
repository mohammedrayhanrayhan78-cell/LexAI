from __future__ import annotations

import logging
from typing import List
import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self) -> None:
        self.provider = settings.EMBEDDING_PROVIDER.lower()
        if self.provider == "gemini":
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY is not configured for embeddings.")
            genai.configure(api_key=settings.GEMINI_API_KEY)
        elif self.provider == "openai":
            from openai import AsyncOpenAI
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not configured for embeddings.")
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")

    async def get_embedding(self, text: str) -> List[float]:
        try:
            if self.provider == "gemini":
                # Using Gemini embed_content API
                response = genai.embed_content(
                    model=f"models/{settings.EMBEDDING_MODEL}",
                    content=text,
                    task_type="retrieval_document",
                )
                return response["embedding"]
            elif self.provider == "openai":
                response = await self.openai_client.embeddings.create(
                    input=[text],
                    model=settings.EMBEDDING_MODEL,
                )
                return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise