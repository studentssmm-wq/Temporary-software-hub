from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.config import DATABASE_URL

# Створюємо базовий клас тут
class Base(DeclarativeBase):
    pass

engine = create_async_engine(
    DATABASE_URL
)

session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)