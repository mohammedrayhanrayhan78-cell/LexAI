from __future__ import annotations

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.crud.crud_chat import chat_crud
from app.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    MessageResponse,
    MessagePairResponse,
)
from app.agent.graph import LegalAgentGraph

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB limit
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conv_in: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationResponse:
    conversation = await chat_crud.create_conversation(db, obj_in=conv_in, user_id=current_user.id)
    logger.info(f"Conversation created: {conversation.id} for user: {current_user.email}")
    return conversation


@router.get("/conversations", response_model=List[ConversationResponse], status_code=status.HTTP_200_OK)
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ConversationResponse]:
    conversations = await chat_crud.get_conversations_by_user(db, user_id=current_user.id)
    return list(conversations)


@router.get("/conversations/{id}/messages", response_model=List[MessageResponse], status_code=status.HTTP_200_OK)
async def get_messages(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[MessageResponse]:
    conversation = await chat_crud.get_conversation_by_id(db, conversation_id=id, user_id=current_user.id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    messages = await chat_crud.get_messages_by_conversation(db, conversation_id=id)
    return list(messages)


@router.post("/conversations/{id}/messages", response_model=MessagePairResponse, status_code=status.HTTP_201_CREATED)
async def post_message(
    id: uuid.UUID,
    content: str = Form(...),
    image: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessagePairResponse:
    conversation = await chat_crud.get_conversation_by_id(db, conversation_id=id, user_id=current_user.id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    image_bytes: Optional[bytes] = None
    user_message_content = content

    if image is not None:
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image type: {image.content_type}. Allowed types: JPEG, PNG, WEBP, HEIC.",
            )
        image_bytes = await image.read()
        if len(image_bytes) > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image size exceeds the maximum limit of 10MB.",
            )
        user_message_content = f"{content}\n[Attached Image: {image.filename}]"

    # 1. Persist user message
    user_message = await chat_crud.create_message(
        db, conversation_id=id, role="user", content=user_message_content
    )

    # 2. Fetch full conversation message history for context
    history_messages = await chat_crud.get_messages_by_conversation(db, conversation_id=id)
    formatted_history = [{"role": m.role, "content": m.content} for m in history_messages]

    # 3. Execute request through the LangGraph Agent workflow
    agent = LegalAgentGraph(db)
    ai_response_content = await agent.run(
        messages=formatted_history,
        user_id=current_user.id,
        query=content,
        image_bytes=image_bytes,
    )

    # 4. Persist assistant response
    assistant_message = await chat_crud.create_message(
        db,
        conversation_id=id,
        role="assistant",
        content=ai_response_content,
    )

    logger.info(f"Agent response generated and persisted for conversation: {id}")
    return MessagePairResponse(
        user_message=user_message,
        assistant_message=assistant_message,
    )