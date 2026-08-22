from aiogram.filters import BaseFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.users.user_repository import find_user_by_id


class AdminFilter(BaseFilter):
    async def __call__(self, message: Message, session: AsyncSession) -> bool:
        user = await find_user_by_id(session, message.from_user.id)
        return bool(user and user.user_role == "admin")
