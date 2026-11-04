from __future__ import annotations

import uuid
from typing import List, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.chat import ConversationCreate, MessageCreate


class CRUDChat:
    async def create_conversation(
        self, db: AsyncSession, obj_in: ConversationCreate, user_id: uuid.UUID
    ) -> Conversation:
        db_obj = Conversation(
            title=obj_in.title,
            user_id=user_id,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_conversations_by_user(
        self, db: AsyncSession, user_id: uuid.UUID
    ) -> Sequence[Conversation]:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return result.scalars().all()

    async def get_conversation_by_id(
        self, db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> Conversation | None:
        result = await db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id, Conversation.user_id == user_id)
        )
        return result.scalars().first()

    async def get_messages_by_conversation(
        self, db: AsyncSession, conversation_id: uuid.UUID
    ) -> Sequence[Message]:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return result.scalars().all()

    async def create_message(
        self, db: AsyncSession, conversation_id: uuid.UUID, role: str, content: str
    ) -> Message:
        db_obj = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


chat_crud = CRUDChat()