from uuid import UUID

from sqlalchemy import select

from app.database.models import QRPass
from sqlalchemy.ext.asyncio import AsyncSession


async def get_pass(session, pass_id: UUID):
    result = await session.execute(
        select(QRPass).where(QRPass.pass_id == pass_id)
    )

    return result.scalar_one_or_none()


async def create_pass(session: AsyncSession, pass_id: UUID, telegram_id: int):
    qr_pass = QRPass(
        pass_id=pass_id,
        telegram_id=telegram_id,
        is_on_territory=False,
    )

    session.add(qr_pass)
    await session.commit()
    await session.refresh(qr_pass)

    return qr_pass


async def toggle_pass(session, qr_pass):
    qr_pass.is_on_territory = not qr_pass.is_on_territory

    await session.commit()

    return qr_pass
