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
from app.services.mailing_service import process_scheduled_mailings


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Запустити бота"),
        BotCommand(command="menu", description="📋 Головне меню"),
        BotCommand(command="qr", description="📲 Отримати свій QR-код"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


async def start_bot():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    await set_bot_commands(bot)

    engine, session_factory = create_db_pool(DATABASE_URL)
    dp.update.middleware(DatabaseMiddleware(session_factory))
    dp.include_routers(qr_router, admin_router, profile_router,
                       registration_router, stats_router)
    asyncio.create_task(process_scheduled_mailings(bot, session_factory))

    print("Бот запущений!")

    try:
        await dp.start_polling(bot)
    finally:
        await engine.dispose()