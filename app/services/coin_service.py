from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import find_user_by_id
from app.repositories.coin_repository import create_coin_transaction


async def process_coin_transaction(session: AsyncSession, telegram_id: int, amount: int, feature: str) -> bool:
    user = await find_user_by_id(session, telegram_id)
    if not user:
        return False
    if amount < 0 and user.coins < abs(amount):
        return False
    user.coins += amount

    await create_coin_transaction(session, telegram_id, amount, feature)
    await session.commit()
    return True
