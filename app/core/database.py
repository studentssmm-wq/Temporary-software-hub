from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_db_pool(database_url: str):
    # Використовуємо NullPool, щоб з'єднання закривалися миттєво
    engine = create_async_engine(
        database_url,
        poolclass=NullPool,
        # pool_size, max_overflow та pool_pre_ping тут більше не потрібні
    )

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    return engine, session_factory