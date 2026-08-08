from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.config import DATABASE_URL


engine = create_async_engine(
    DATABASE_URL
)


def create_db_pool(database_url: str):
    # Налаштовуємо пул з'єднань
    engine = create_async_engine(
        database_url,
        pool_size=10,  # 10 постійних відкритих з'єднань у пулі
        max_overflow=10,  # Ще 10 додаткових з'єднань при пікових навантаженнях
        pool_pre_ping=True,  # Перевірка "живучості" з'єднання перед використанням
    )

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    return engine, session_factory
