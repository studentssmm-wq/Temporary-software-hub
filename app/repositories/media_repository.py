from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import BotMedia


async def get_media(session: AsyncSession, name: str) -> str | None:
    """Отримує file_id картинки з бази за її назвою"""
    result = await session.execute(select(BotMedia).where(BotMedia.name == name))
    media = result.scalar_one_or_none()
    return media.file_id if media else None


async def update_media(session: AsyncSession, name: str, file_id: str):
    """Оновлює або створює новий запис з file_id"""
    result = await session.execute(select(BotMedia).where(BotMedia.name == name))
    media = result.scalar_one_or_none()

    if media:
        media.file_id = file_id
    else:
        media = BotMedia(name=name, file_id=file_id)
        session.add(media)

    await session.commit()