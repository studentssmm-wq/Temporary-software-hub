from aiogram import Bot, Dispatcher

from app.config import BOT_TOKEN, DATABASE_URL
from app.handlers.qr_handler import qr
from app.middlewares.database_middleware import DatabaseMiddleware
from app.database.database import create_db_pool

async def start_bot():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    engine, session_factory = create_db_pool(DATABASE_URL)
    dp.update.middleware(DatabaseMiddleware(session_factory))
    dp.include_router(qr)
    try:
        await dp.start_polling(bot)
    finally:
        # Коректно закриваємо пул з'єднань при зупинці бота
        await engine.dispose()
