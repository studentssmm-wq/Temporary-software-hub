from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.models import ScheduleMedia


async def add_schedule_photo(session: AsyncSession, event_day: int, file_id: str):
    media = ScheduleMedia(event_day=event_day, file_id=file_id)
    session.add(media)
    await session.commit()


async def get_schedule_days(session: AsyncSession) -> list[int]:
    result = await session.execute(
        select(ScheduleMedia.event_day).distinct().order_by(
            ScheduleMedia.event_day)
    )
    return list(result.scalars().all())


async def delete_schedule_for_day(session: AsyncSession, event_day: int):
    await session.execute(
        delete(ScheduleMedia).where(ScheduleMedia.event_day == event_day)
    )
    await session.commit()


async def get_schedule_photos_by_day(session: AsyncSession, event_day: int) -> list[str]:
    """Отримує всі фотографії розкладу для обраного дня, відсортовані за часом додавання"""
    result = await session.execute(
        select(ScheduleMedia.file_id)
        .where(ScheduleMedia.event_day == event_day)
        .order_by(ScheduleMedia.id)  # Щоб зберігався порядок завантаження
    )
    return list(result.scalars().all())
