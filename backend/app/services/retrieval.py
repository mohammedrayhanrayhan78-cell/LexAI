from __future__ import annotations

import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.document_chunk import DocumentChunk
from app.models.document import Document
from app.core.embeddings import EmbeddingService
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(self) -> None:
        # Lazy-init: EmbeddingService is created on first use so the app can
        # start even when embedding keys are absent (graceful degradation).
        self._embedding_service: EmbeddingService | None = None

    @property
    def embedding_service(self) -> EmbeddingService:
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    async def search_relevant_chunks(
        self, db: AsyncSession, query: str, user_id: uuid.UUID, top_k: int = settings.TOP_K_RETRIEVAL
    ) -> List[str]:
        try:
            query_embedding = await self.embedding_service.get_embedding(
                query, task_type="retrieval_query"
            )
            
            # Execute cosine distance similarity search restricted to documents owned by user
            stmt = (
                select(DocumentChunk.content)
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(Document.user_id == user_id)
                .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
                .limit(top_k)
            )
            
            result = await db.execute(stmt)
            chunks = result.scalars().all()
            return list(chunks)
        except Exception as e:
            logger.error(f"Vector similarity search failed: {e}")
            return []


retrieval_service = RetrievalService()
