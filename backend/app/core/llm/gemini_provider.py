from __future__ import annotations

import asyncio
import io
import logging
from typing import List, Dict, Any
import google.generativeai as genai
from PIL import Image

from app.core.llm.base import BaseLLMProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model_name = settings.GEMINI_MODEL

    async def generate(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        try:
            gemini_history = []
            for msg in messages[:-1]:
                role = "user" if msg["role"] == "user" else "model"
                gemini_history.append({"role": role, "parts": [msg["content"]]})
            
            latest_message = messages[-1]["content"] if messages else ""

            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction="You are LexAI, an expert production-ready AI Legal Assistant specializing in Indian law and judicial procedures."
            )
            chat = model.start_chat(history=gemini_history)

            response = await asyncio.wait_for(
                chat.send_message_async(latest_message),
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )
            content = response.text
            if not content:
                raise ValueError("Received empty response from Gemini.")
            return content
        except asyncio.TimeoutError:
            logger.error("Gemini generation timed out.")
            raise
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise

    async def generate_with_image(
        self, messages: List[Dict[str, str]], image_bytes: bytes, **kwargs: Any
    ) -> str:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            gemini_history = []
            for msg in messages[:-1]:
                role = "user" if msg["role"] == "user" else "model"
                gemini_history.append({"role": role, "parts": [msg["content"]]})
            
            latest_message = messages[-1]["content"] if messages else "Analyze this legal image."

            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction="You are LexAI, an expert production-ready AI Legal Assistant. Analyze the provided image thoroughly in a legal context."
            )
            chat = model.start_chat(history=gemini_history)

            # Send both text prompt and PIL image to Gemini multimodal model
            response = await asyncio.wait_for(
                chat.send_message_async([latest_message, image]),
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )
            content = response.text
            if not content:
                raise ValueError("Received empty response from Gemini vision model.")
            return content
        except asyncio.TimeoutError:
            logger.error("Gemini vision generation timed out.")
            raise
        except Exception as e:
            logger.error(f"Gemini vision generation failed: {e}")
            raise