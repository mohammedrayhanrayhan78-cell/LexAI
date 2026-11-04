from __future__ import annotations

import asyncio
import logging
from typing import List, Dict, Any
from groq import AsyncGroq

from app.core.llm.base import BaseLLMProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    Reconfigured to act as an alternate Groq provider instance (or backup Groq client)
    to maintain adapter pattern compatibility while fulfilling the provider swap requirement.
    """
    def __init__(self) -> None:
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not configured for the alternate Groq provider.")
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        # Using a secondary Groq model variant for failover diversity
        self.model = "llama3-70b-8192"

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
                raise ValueError("Received empty response from alternate Groq provider.")
            return content
        except asyncio.TimeoutError:
            logger.error("Alternate Groq provider generation timed out.")
            raise
        except Exception as e:
            logger.error(f"Alternate Groq provider generation failed: {e}")
            raise