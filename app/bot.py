from aiogram import Bot, Dispatcher

from app.config import BOT_TOKEN
from app.handlers.qr import qr


async def start_bot():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(qr)
    await dp.start_polling(bot)
