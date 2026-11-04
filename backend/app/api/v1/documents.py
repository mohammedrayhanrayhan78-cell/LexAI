from __future__ import annotations

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import logging

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.pdf_extraction import PDFExtractionService
from app.services.chunking import TextChunker
from app.core.embeddings import EmbeddingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])
embedding_service = EmbeddingService()

MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB limit


@router.post("/upload", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported.",
        )

    content_type = file.content_type
    if content_type and content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid MIME type. Must be application/pdf.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the maximum limit of 15MB.",
        )

    # 1. Create Document record
    document = Document(
        id=uuid.uuid4(),
        user_id=current_user.id,
        filename=file.filename,
        status="processing",
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    try:
        # 2. Extract text with page numbers
        pages = PDFExtractionService.extract_text_with_pages(file_bytes)
        if not pages:
            document.status = "failed"
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract any text from the provided PDF.",
            )

        # 3. Chunk and embed each page / text segment
        chunk_counter = 0
        for page_info in pages:
            page_num = page_info["page_number"]
            page_text = page_info["content"]
            
            chunks = TextChunker.chunk_text(page_text)
            for chunk_content in chunks:
                formatted_chunk = f"[Source: {file.filename}, Page {page_num}]\n{chunk_content}"
                embedding = await embedding_service.get_embedding(formatted_chunk)
                
                db_chunk = DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=document.id,
                    content=formatted_chunk,
                    embedding=embedding,
                    chunk_index=chunk_counter,
                )
                db.add(db_chunk)
                chunk_counter += 1

        document.status = "indexed"
        await db.commit()

        logger.info(f"Document {document.id} uploaded, extracted, and indexed successfully with {chunk_counter} chunks.")
        return {
            "id": str(document.id),
            "filename": document.filename,
            "status": "indexed",
            "message": "Document successfully uploaded and indexed for RAG."
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Document indexing pipeline failed: {e}")
        document.status = "failed"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process and index the PDF document.",
        )


@router.get("", response_model=List[dict], status_code=status.HTTP_200_OK)
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    result = await db.execute(
        select(Document).where(Document.user_id == current_user.id).order_by(Document.upload_date.desc())
    )
    documents = result.scalars().all()
    return [
        {
            "id": str(doc.id),
            "filename": doc.filename,
            "status": doc.status,
            "upload_date": doc.upload_date.isoformat(),
        }
        for doc in documents
    ]


@router.delete("/{id}", status_code=status.HTTP_200_OK)
async def delete_document(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    result = await db.execute(
        select(Document).where(Document.id == id, Document.user_id == current_user.id)
    )
    document = result.scalars().first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    await db.delete(document)
    await db.commit()
    logger.info(f"Document {id} and its associated chunks were deleted.")
    return {"status": "success", "message": "Document deleted successfully."}