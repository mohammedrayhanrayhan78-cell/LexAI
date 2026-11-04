from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from app.core.llm.base import BaseLLMProvider
from app.core.llm.groq_provider import GroqProvider
from app.core.llm.gemini_provider import GeminiProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMRouter:
    def __init__(self) -> None:
        self.providers: Dict[str, BaseLLMProvider] = {}
        
        try:
            if settings.GROQ_API_KEY:
                self.providers["groq"] = GroqProvider()
        except Exception as e:
            logger.warning(f"Could not initialize Groq provider: {e}")

        try:
            if settings.GEMINI_API_KEY:
                self.providers["gemini"] = GeminiProvider()
        except Exception as e:
            logger.warning(f"Could not initialize Gemini provider: {e}")

    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        primary = settings.DEFAULT_LLM_PROVIDER.lower()
        
        provider_order: List[str] = []
        if primary in self.providers:
            provider_order.append(primary)
        
        for name in self.providers:
            if name not in provider_order:
                provider_order.append(name)

        if not provider_order:
            logger.error("No LLM providers are configured or available.")
            return "Error: No AI providers are currently configured on the server."

        system_prompt = {
            "role": "system",
            "content": (
                "You are LexAI, a professional AI Legal Assistant specialized EXCLUSIVELY in Indian law. "
                "Answer strictly according to Indian legislation, statutes, and the Indian judiciary system — "
                "the Indian Penal Code (IPC) / Bharatiya Nyaya Sanhita (BNS), the Indian Contract Act 1872, "
                "the Constitution of India, CrPC/BNSS, Evidence Act/BSA, and other applicable Indian central "
                "and state laws. NEVER cite US, UK, or other foreign statutes, case law, or legal systems — "
                "if a concept has no direct Indian equivalent, say so explicitly rather than substituting "
                "foreign law.\n\n"
                "ALWAYS format responses in clean markdown:\n"
                "- Use ## headings to break the answer into sections\n"
                "- Use bullet points (- ) or numbered lists (1. 2. 3.) for enumerable items — one point per line, "
                "never combine multiple points into one paragraph\n"
                "- Bold key terms, section numbers, and act names using **term**\n"
                "- Keep any explanatory paragraph short (2-3 sentences max) and always follow it with a "
                "structured list where applicable\n"
                "- Never write a dense wall of text — structure every answer like a well-organized legal "
                "textbook, not continuous prose"
            )
        }
        
        full_messages = [system_prompt] + messages

        last_exception = None
        for provider_name in provider_order:
            provider = self.providers[provider_name]
            try:
                logger.info(f"Attempting LLM generation using provider: {provider_name}")
                response = await provider.generate(full_messages)
                return response
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}. Attempting fallback...")
                last_exception = e

        logger.error(f"All LLM providers failed. Last error: {last_exception}")
        return "Error: All available AI providers failed to respond. Please try again later."

    async def generate_response_with_image(self, messages: List[Dict[str, str]], image_bytes: bytes) -> str:
        # Vision requests must be routed exclusively to Gemini
        if "gemini" not in self.providers:
            logger.error("Vision request received, but Gemini provider is not configured or available.")
            return "Error: Vision processing requires Gemini, which is not configured on this server."

        system_prompt = {
            "role": "system",
            "content": "You are LexAI, a professional production-grade AI Legal Assistant analyzing legal documents and images."
        }
        full_messages = [system_prompt] + messages

        try:
            logger.info("Routing vision request exclusively to Gemini provider.")
            response = await self.providers["gemini"].generate_with_image(full_messages, image_bytes)
            return response
        except Exception as e:
            logger.error(f"Gemini vision generation failed: {e}")
            return "Error: Failed to process the image with Gemini vision model. Please ensure a valid image was uploaded."


llm_router = LLMRouter()