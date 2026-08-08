from aiogram import Bot, Dispatcher

from app.config import BOT_TOKEN
from app.handlers.qr_handler import qr
from app.middlewares.database_middleware import DatabaseMiddleware


async def start_bot():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.update.middleware(DatabaseMiddleware())
    dp.include_router(qr)
    await dp.start_polling(bot)
