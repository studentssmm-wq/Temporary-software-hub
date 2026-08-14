import asyncio
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from app.database.models import ScheduledMailing
from app.repositories.user_repository import get_users_for_broadcast


async def process_scheduled_mailings(bot: Bot, session_maker):
    """
    Фонова задача, яка перевіряє БД кожну хвилину і розсилає повідомлення.
    """
    while True:
        try:
            async with session_maker() as session:
                now = datetime.now()
                query = select(ScheduledMailing).where(
                    ScheduledMailing.status == "pending",
                    ScheduledMailing.send_at <= now
                )
                result = await session.execute(query)
                mailings = result.scalars().all()

                for mailing in mailings:
                    mailing.status = "processing"
                    await session.commit()

                    users_ids = await get_users_for_broadcast(session, mailing.audience)

                    if users_ids:
                        for user_id in users_ids:
                            try:
                                if mailing.media_type == "photo":
                                    await bot.send_photo(chat_id=user_id, photo=mailing.media_file_id,
                                                         caption=mailing.message_text)
                                elif mailing.media_type == "video":
                                    await bot.send_video(chat_id=user_id, video=mailing.media_file_id,
                                                         caption=mailing.message_text)
                                elif mailing.media_type == "document":
                                    await bot.send_document(chat_id=user_id, document=mailing.media_file_id,
                                                            caption=mailing.message_text)
                                else:
                                    await bot.send_message(chat_id=user_id, text=mailing.message_text)
                            except TelegramAPIError:
                                pass
                            await asyncio.sleep(0.05)

                    mailing.status = "sent"
                    await session.commit()

        except Exception as e:
            print(f"Помилка в планувальнику розсилок: {e}")

        await asyncio.sleep(60)