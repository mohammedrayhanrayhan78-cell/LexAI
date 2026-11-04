from __future__ import annotations

import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.schemas.auth import UserRegister
from app.core.security import hash_password


class CRUDUser:
    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def get_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    async def create(self, db: AsyncSession, obj_in: UserRegister) -> User:
        db_obj = User(
            full_name=obj_in.full_name,
            email=obj_in.email,
            hashed_password=hash_password(obj_in.password),
            is_active=True,
            is_verified=False,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


user_crud = CRUDUser()