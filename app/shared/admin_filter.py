from aiogram.filters import BaseFilter
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import ADMIN_IDS
from app.features.users.user_repository import find_user_by_id


async def is_admin(user_id: int, session: AsyncSession) -> bool:
    if user_id in ADMIN_IDS:
        return True
    user = await find_user_by_id(session, user_id)
    return bool(user and user.user_role == "admin")


class AdminFilter(BaseFilter):
    async def __call__(self, event, session: AsyncSession) -> bool:
        return bool(event.from_user and await is_admin(event.from_user.id, session))
