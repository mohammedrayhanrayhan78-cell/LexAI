from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import logging

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.chunking import TextChunker
from app.core.embeddings import EmbeddingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["RAG Documents"])

# Lazy singleton — created on first request so startup never fails due to missing keys
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


@router.post("/documents/{id}/index", status_code=status.HTTP_200_OK)
async def index_document(
    id: uuid.UUID,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    raw_text = payload.get("text")
    if not raw_text or not isinstance(raw_text, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid 'text' field is required for indexing.")

    # Verify document ownership
    result = await db.execute(
        select(Document).where(Document.id == id, Document.user_id == current_user.id)
    )
    document = result.scalars().first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    try:
        embedding_service = get_embedding_service()
        # 1. Chunk text
        chunks = TextChunker.chunk_text(raw_text)

        # 2. Generate embeddings and persist chunks
        for idx, chunk_content in enumerate(chunks):
            embedding = await embedding_service.get_embedding(
                chunk_content, task_type="retrieval_document"
            )
            db_chunk = DocumentChunk(
                document_id=document.id,
                content=chunk_content,
                embedding=embedding,
                chunk_index=idx,
            )
            db.add(db_chunk)

        document.status = "indexed"
        await db.commit()

        logger.info(f"Successfully indexed document {id} with {len(chunks)} chunks.")
        return {"status": "success", "message": f"Indexed {len(chunks)} chunks for document {id}."}
    except Exception as e:
        logger.error(f"Failed to index document {id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Document indexing failed.")
