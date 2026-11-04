from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class ConversationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessagePairResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse

    class Config:
        from_attributes = True