import logging
from aiogram import Bot, Dispatcher

# Імпортуємо токен з твого конфігу
from app.config import BOT_TOKEN

# Імпортуємо мідлвар
from app.middlewares.database_middleware import DatabaseMiddleware

# Імпортуємо роутери (твої хендлери)
from app.handlers.qr_handler import qr as qr_router
from app.handlers.registration import router as registration_router

async def start_bot():
    # Налаштовуємо відображення логів у терміналі
    logging.basicConfig(level=logging.INFO)
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # 1. Підключаємо мідлвар для роботи з базою даних
    dp.update.middleware(DatabaseMiddleware())

    # 2. Підключаємо роутери (хендлери)
    dp.include_router(registration_router)
    dp.include_router(qr_router)

    print("Бот запущено! Йди в Telegram і пиши /start")
    
    # 3. Запускаємо поллінг
    await dp.start_polling(bot)