from __future__ import annotations

from typing import List
from app.core.config import settings


class TextChunker:
    @staticmethod
    def chunk_text(text: str) -> List[str]:
        chunk_size = settings.CHUNK_SIZE
        overlap = settings.CHUNK_OVERLAP
        
        if not text:
            return []

        chunks: List[str] = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunk = text[start:end]
            chunks.append(chunk)
            if end == text_length:
                break
            start += chunk_size - overlap

        return chunks