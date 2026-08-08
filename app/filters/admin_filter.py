from aiogram.filters import BaseFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.models import User
from app.repositories.user_repository import find_user_by_id


class AdminFilter(BaseFilter):
    async def __call__(self, message: Message, session: AsyncSession) -> bool:
        user = await find_user_by_id(session, message.from_user.id)
        return bool(user and user.user_role == "admin")
