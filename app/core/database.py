from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
# Імпортуємо URL бази даних з твого конфігу
from app.core.config import DATABASE_URL

# Створюємо глобальний engine та session_maker, які тепер можна імпортувати куди завгодно
engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,
)

session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Оновлюємо стару функцію, щоб bot.py продовжував працювати без змін
def create_db_pool(database_url: str):
    return engine, session_maker