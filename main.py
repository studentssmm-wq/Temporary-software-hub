
import asyncio
from app.core.background_tasks import process_redis_queue
from app.bot import start_bot

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("Роботу бота зупинено.")
