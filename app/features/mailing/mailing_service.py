import asyncio
from datetime import datetime
from sqlalchemy import select
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.models import ScheduledMailing
from app.features.users.user_repository import get_users_for_broadcast

# Ініціалізуємо планувальник глобально або в main.py
scheduler = AsyncIOScheduler(timezone="Europe/Kyiv")

async def execute_mailing(mailing_id: int, bot: Bot, session_maker):
    """
    Функція, яка викликається планувальником у точний час розсилки.
    Вона відкриває БД лише на час фактичної відправки.
    """
    try:
        async with session_maker() as session:
            # Отримуємо розсилку за ID
            mailing = await session.get(ScheduledMailing, mailing_id)
            
            if not mailing or mailing.status != "pending":
                return

            mailing.status = "processing"
            await session.commit()

            users_ids = await get_users_for_broadcast(session, mailing.audience)

            if users_ids:
                for user_id in users_ids:
                    try:
                        if mailing.media_type == "photo":
                            await bot.send_photo(chat_id=user_id, photo=mailing.media_file_id, caption=mailing.message_text)
                        elif mailing.media_type == "video":
                            await bot.send_video(chat_id=user_id, video=mailing.media_file_id, caption=mailing.message_text)
                        elif mailing.media_type == "document":
                            await bot.send_document(chat_id=user_id, document=mailing.media_file_id, caption=mailing.message_text)
                        else:
                            await bot.send_message(chat_id=user_id, text=mailing.message_text)
                    except TelegramAPIError:
                        pass
                    await asyncio.sleep(0.05)

            mailing.status = "sent"
            await session.commit()

    except Exception as e:
        print(f"Помилка під час виконання розсилки {mailing_id}: {e}")
        
async def restore_pending_mailings_on_startup(bot: Bot, session_maker):
    """
    Викликати один раз при запуску бота (startup event).
    """
    async with session_maker() as session:
        query = select(ScheduledMailing).where(ScheduledMailing.status == "pending")
        result = await session.execute(query)
        mailings = result.scalars().all()

        for mailing in mailings:
            # Якщо час відправки вже минув, поки бот був вимкнений - відправляємо зараз
            run_date = mailing.send_at if mailing.send_at > datetime.now() else datetime.now()
            
            scheduler.add_job(
                execute_mailing,
                trigger='date',
                run_date=run_date,
                args=[mailing.id, bot, session_maker],
                id=f"mailing_{mailing.id}",
                replace_existing=True
            )
    
    # Запускаємо планувальник, якщо він ще не запущений
    if not scheduler.running:
        scheduler.start()