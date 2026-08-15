from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import CoinTransaction


async def create_coin_transaction(session: AsyncSession, telegram_id: int, amount: int, feature: str) -> CoinTransaction:
    transaction = CoinTransaction(
        telegram_id=telegram_id,
        amount=amount,
        feature=feature
    )
    session.add(transaction)
    return transaction
