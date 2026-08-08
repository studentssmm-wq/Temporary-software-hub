import asyncio
import threading
from server import run_dummy_server
from app.bot import start_bot
import app.database as _

if __name__ == "__main__":
    # 1. Запускаємо фейковий сервер у фоновому потоці (для Render)
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    # 2. Запускаємо асинхронний процес бота
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("Бот зупинений.")