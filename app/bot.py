import os
import asyncio
import uvicorn
from fastapi import FastAPI
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault
from fastapi.middleware.cors import CORSMiddleware
from app.api.webapp_routes import webapp_router
from app.config import BOT_TOKEN, DATABASE_URL
from app.database.database import create_db_pool
from app.handlers.admin_handler import admin_router
from app.handlers.profile_handler import profile_router
from app.handlers.qr_handler import qr_router
from app.handlers.registration_handler import registration_router
from app.handlers.stats_handler import stats_router
from app.middlewares.database_middleware import DatabaseMiddleware
from app.services.mailing_service import process_scheduled_mailings

from app.api.webhook_routes import mono_router


async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Запустити бота"),
        BotCommand(command="menu", description="📋 Головне меню"),
        # BotCommand(command="qr", description="📲 Отримати свій QR-код"),
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

    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        # У майбутньому замініть "*" на URL вашого Vercel, напр. ["https://fortunecookie-seven.vercel.app"]
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.bot = bot
    app.state.session_factory = session_factory
    app.include_router(mono_router)
    app.include_router(webapp_router)
    port = int(os.environ.get("PORT", 8000))

    config = uvicorn.Config(app=app, host="0.0.0.0", port=port, loop="asyncio")
    server = uvicorn.Server(config)

    print(f"🚀 Запуск Telegram-бота та FastAPI сервера (порт {port})...")

    try:
        server_task = asyncio.create_task(server.serve())
        bot_task = asyncio.create_task(dp.start_polling(bot))

        await asyncio.gather(server_task, bot_task)
    except asyncio.CancelledError:
        print("Зупинка задач...")
    finally:
        await engine.dispose()
