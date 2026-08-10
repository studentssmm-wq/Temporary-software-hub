import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault

from app.config import BOT_TOKEN, DATABASE_URL
from app.database.database import create_db_pool
from app.handlers.admin_handler import admin_router
from app.handlers.profile_handler import profile_router
from app.handlers.qr_handler import qr_router
from app.handlers.registration_handler import registration_router
from app.handlers.stats_handler import stats_router
from app.middlewares.database_middleware import DatabaseMiddleware


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Запустити бота"),
        BotCommand(command="menu", description="📋 Головне меню"), # <--- Додали рядок
        BotCommand(command="qr", description="📲 Отримати свій QR-код"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


async def start_bot():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    engine, session_factory = create_db_pool(DATABASE_URL)

    dp.update.middleware(DatabaseMiddleware(session_factory))
    dp.include_routers(qr_router, admin_router,
                       registration_router, stats_router)

    await set_bot_commands(bot)
    print("Бот запущено!")

    try:
        await dp.start_polling(bot)
    finally:
        await engine.dispose()
