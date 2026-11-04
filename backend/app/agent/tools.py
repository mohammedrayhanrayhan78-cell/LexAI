from __future__ import annotations

import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.document import Document
from app.services.retrieval import retrieval_service
from app.core.llm.router import llm_router

logger = logging.getLogger(__name__)


class AgentTools:
    @staticmethod
    async def summarize_document(db: AsyncSession, user_id: uuid.UUID, query: str) -> str:
        try:
            # Retrieve all chunks associated with the user's documents
            chunks = await retrieval_service.search_relevant_chunks(db, query=query, user_id=user_id, top_k=10)
            if not chunks:
                return "No documents found to summarize."

            doc_text = "\n".join(chunks)
            prompt = [
                {"role": "system", "content": "You are LexAI. Summarize the following legal document excerpts concisely and accurately."},
                {"role": "user", "content": f"Please provide a comprehensive summary of these excerpts:\n{doc_text}"}
            ]
            summary = await llm_router.generate_response(prompt)
            return summary
        except Exception as e:
            logger.error(f"Summarize tool failed: {e}")
            return "Error executing document summarization."

    @staticmethod
    async def compare_documents(db: AsyncSession, user_id: uuid.UUID, query: str) -> str:
        try:
            chunks = await retrieval_service.search_relevant_chunks(db, query=query, user_id=user_id, top_k=8)
            if not chunks:
                return "Insufficient document data found for comparison."

            doc_text = "\n---\n".join(chunks)
            prompt = [
                {"role": "system", "content": "You are LexAI. Compare and contrast the legal clauses or provisions found in the provided excerpts."},
                {"role": "user", "content": f"Compare these legal excerpts based on the query '{query}':\n{doc_text}"}
            ]
            comparison = await llm_router.generate_response(prompt)
            return comparison
        except Exception as e:
            logger.error(f"Compare tool failed: {e}")
            return "Error executing document comparison."