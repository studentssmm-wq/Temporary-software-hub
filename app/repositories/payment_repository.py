from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Payment


async def create_payment(session: AsyncSession, telegram_id: int, amount: int, invoice_id: str) -> Payment:
    new_payment = Payment(
        telegram_id=telegram_id,
        amount=amount,
        status="PENDING",
        invoice_id=invoice_id
    )
    session.add(new_payment)
    await session.commit()
    await session.refresh(new_payment)
    return new_payment


async def get_payment_by_invoice(session: AsyncSession, invoice_id: str) -> Payment:
    result = await session.execute(
        select(Payment).where(Payment.invoice_id == invoice_id)
    )
    return result.scalar_one_or_none()


async def update_payment_status(session: AsyncSession, payment: Payment, status: str) -> Payment:
    payment.status = status
    await session.commit()
    await session.refresh(payment)
    return payment
