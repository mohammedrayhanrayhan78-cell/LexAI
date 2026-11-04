from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """
        Generate a text response from the LLM provider given a list of messages.
        Messages format: [{"role": "user" | "assistant" | "system", "content": "..."}]
        """
        pass

    @abstractmethod
    async def generate_with_image(
        self, messages: List[Dict[str, str]], image_bytes: bytes, **kwargs: Any
    ) -> str:
        """
        Generate a response given conversation messages and an image attachment.
        """
        pass