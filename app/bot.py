from aiogram import Bot, Dispatcher

from app.config import BOT_TOKEN
from app.handlers.qr_handler import qr_router
from app.handlers.admin_handler import admin_router
from app.middlewares.database_middleware import DatabaseMiddleware

from aiogram.types import BotCommand


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Запустити бота / Мій QR"),
        BotCommand(command="qr", description="📲 Отримати свій QR-код"),
        BotCommand(command="admin", description="👑 Панель адміністратора"),
    ]

    await bot.set_my_commands(commands)


async def start_bot():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.update.middleware(DatabaseMiddleware())
    dp.include_routers(qr_router, admin_router)
    await set_bot_commands(bot)
    print("Бот успішно запущений!")
    await dp.start_polling(bot)
