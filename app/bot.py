import asyncio
import logging
import os
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.types import BotCommand, BotCommandScopeDefault
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.webapp_routes import webapp_router
from app.api.webhook_routes import mono_router
from app.core.config import BOT_TOKEN, ENABLE_MAILINGS, ENABLE_PAYMENTS, IS_DEVELOPMENT, validate_settings
from app.core.database import engine, session_maker, assert_database_ready
from app.core.middlewares.database_middleware import DatabaseMiddleware
from app.core.middlewares.development_guard import DevelopmentUpdateGuard, DevelopmentRequestGuard
from app.features.admin.admin_handler import admin_router
from app.features.analytics.stats_handler import stats_router
from app.features.events.event_handler import event_router
from app.features.mailing.mailing_service import restore_pending_mailings_on_startup, scheduler
from app.features.menu.menu_handler import menu_router
from app.features.menu.navigation import navigation_router
from app.features.qr_pass.qr_handler import qr_router
from app.features.songbook.song_handler import song_router
from app.features.support.handlers import support_router, support_admin_router
from app.features.ticketing.admin import dp as ticket_admin_router
from app.features.ticketing.purchase import dp as ticket_router
from app.features.ticketing.runtime import configure_ticketing
from app.features.users.profile_handler import profile_router
from app.features.users.registration_handler import registration_router, start_router

logger=logging.getLogger(__name__)

async def set_bot_commands(bot):
    await bot.set_my_commands([
        BotCommand(command="start",description="Запустити бота"),
        BotCommand(command="menu",description="Головне меню"),
        BotCommand(command="tickets",description="Квитки та події"),
        BotCommand(command="support",description="Питання та підтримка"),
        BotCommand(command="cancel",description="Скасувати поточну дію"),
    ],scope=BotCommandScopeDefault())


def create_app(bot, session_factory=session_maker):
    app=FastAPI()
    origins=[item.strip() for item in os.getenv("CORS_ORIGINS", "").split(",") if item.strip()]
    if origins:
        app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,allow_methods=["GET","POST"],allow_headers=["Authorization","Content-Type"])
    app.state.bot=bot
    app.state.session_factory=session_factory
    if ENABLE_PAYMENTS:
        app.include_router(mono_router)
    app.include_router(webapp_router)

    @app.get("/")
    async def health():
        return {"status":"OK"}
    return app


async def start_bot():
    validate_settings()
    bot=Bot(token=BOT_TOKEN)
    development_recipients=set()
    if IS_DEVELOPMENT:
        bot.session.middleware(DevelopmentRequestGuard(development_recipients))
    tasks=[]
    server=None
    try:
        await assert_database_ready()
        identity=await bot.get_me()
        official={"students_nulp_official_bot","tickets_nulp_bot","students_nulp_support_bot"}
        if IS_DEVELOPMENT and (identity.username or "").lower() in official:
            raise RuntimeError("Development cannot use an official production bot token")
        await configure_ticketing(bot,session_maker)
        dp=Dispatcher(events_isolation=SimpleEventIsolation())
        if IS_DEVELOPMENT:
            dp.update.outer_middleware(DevelopmentUpdateGuard(development_recipients))
        dp.update.outer_middleware(DatabaseMiddleware(session_maker))
        dp.include_routers(navigation_router,start_router,menu_router,support_admin_router,support_router,
            ticket_admin_router,ticket_router,qr_router,event_router,admin_router,profile_router,
            registration_router,stats_router,song_router)
        await set_bot_commands(bot)
        if ENABLE_MAILINGS:
            await restore_pending_mailings_on_startup(bot,session_maker)
        app=create_app(bot)
        server=uvicorn.Server(uvicorn.Config(app=app,host="127.0.0.1" if IS_DEVELOPMENT else "0.0.0.0",port=int(os.getenv("PORT","8000")),loop="asyncio",access_log=False))
        tasks=[asyncio.create_task(server.serve()),asyncio.create_task(dp.start_polling(bot,close_bot_session=False))]
        if ENABLE_PAYMENTS and not IS_DEVELOPMENT:
            from scripts.register_mono_webhook import setup_mono_webhook
            for _ in range(100):
                if server.started:
                    break
                if any(task.done() for task in tasks):
                    raise RuntimeError('API did not start before Monobank webhook registration')
                await asyncio.sleep(0.1)
            if not server.started:
                raise RuntimeError('API startup timed out')
            webhook_results = await setup_mono_webhook()
            app.state.mono_webhooks_registered = webhook_results
            if not all(webhook_results):
                logger.error('Monobank auto-confirmation is not fully connected. Bot continues; verify payments manually until webhook setup succeeds.')
        done,pending=await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        if server:
            server.should_exit=True
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks,return_exceptions=True)
        if scheduler.running:
            scheduler.shutdown(wait=False)
        await bot.session.close()
        await engine.dispose()
