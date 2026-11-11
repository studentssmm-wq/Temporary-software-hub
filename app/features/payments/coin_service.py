from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.models import User
from app.features.payments.coin_repository import create_coin_transaction

async def process_coin_transaction(session: AsyncSession, telegram_id: int, amount: int, feature: str) -> bool:

    if not isinstance(amount,int) or isinstance(amount,bool) or not feature or len(feature)>50:
        return False
    statement=update(User).where(User.telegram_id==telegram_id)
    if amount<0:
        statement=statement.where(User.coins>=-amount)
    updated=(await session.execute(statement.values(coins=User.coins+amount).returning(User.telegram_id).execution_options(synchronize_session=False))).scalar_one_or_none()
    if updated is None:
        await session.rollback()
        return False
    await create_coin_transaction(session,telegram_id,amount,feature)
    await session.commit()
    return True
