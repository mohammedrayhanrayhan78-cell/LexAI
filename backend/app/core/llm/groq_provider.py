from __future__ import annotations

import asyncio
import logging
from typing import List, Dict, Any
from groq import AsyncGroq

from app.core.llm.base import BaseLLMProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class GroqProvider(BaseLLMProvider):
    def __init__(self) -> None:
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not configured.")
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL

    async def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        try:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                ),
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Received empty response from Groq.")
            return content
        except asyncio.TimeoutError:
            logger.error("Groq generation timed out.")
            raise
        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            raise

    async def generate_with_image(
        self, messages: List[Dict[str, str]], image_bytes: bytes, **kwargs: Any
    ) -> str:
        raise NotImplementedError("Groq does not support vision input in this integration")