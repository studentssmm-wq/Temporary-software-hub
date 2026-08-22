import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.payments.payment_repository import create_payment
from app.core.config import MONO_JAR_URL


async def generate_payment_link(session: AsyncSession, telegram_id: int) -> tuple[str, str]:
    short_id = uuid.uuid4().hex[:8]
    unique_comment = f"pay_{short_id}"
    await create_payment(session, telegram_id, amount=0, invoice_id=unique_comment)

    base_url = MONO_JAR_URL.rstrip("/")
    payment_link = f"{base_url}?t={unique_comment}"
    return unique_comment, payment_link
