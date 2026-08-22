from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_db_pool(database_url: str):
    # Налаштовуємо пул з'єднань
    engine = create_async_engine(
        database_url,
        pool_size=10,         # 10 постійних відкритих з'єднань
        max_overflow=10,      # Ще 10 резервних
        pool_pre_ping=True,   # 🔥 САМЕ ЦЕЙ ПАРАМЕТР ФІКСИТЬ ВАШУ ПОМИЛКУ
    )

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    return engine, session_factory
