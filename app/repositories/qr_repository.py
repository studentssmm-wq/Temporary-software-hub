from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import QRPass


async def get_pass(
    session: AsyncSession,
    pass_id: UUID,
) -> QRPass | None:

    result = await session.execute(
        select(QRPass).where(
            QRPass.pass_id == pass_id
        )
    )

    return result.scalar_one_or_none()


async def get_pass_by_user(
    session: AsyncSession,
    telegram_id: int,
) -> QRPass | None:

    result = await session.execute(
        select(QRPass).where(
            QRPass.telegram_id == telegram_id
        )
    )

    return result.scalar_one_or_none()


async def create_pass(
    session: AsyncSession,
    pass_id: UUID,
    telegram_id: int,
) -> QRPass:

    qr_pass = QRPass(
        pass_id=pass_id,
        telegram_id=telegram_id,
        is_on_territory=False,
    )

    session.add(qr_pass)

    await session.commit()
    await session.refresh(qr_pass)

    return qr_pass


async def toggle_pass(
    session: AsyncSession,
    qr_pass: QRPass,
) -> QRPass:

    qr_pass.is_on_territory = not qr_pass.is_on_territory

    await session.commit()
    await session.refresh(qr_pass)

    return qr_pass


async def get_users_on_territory_count(session: AsyncSession):
    count = await session.scalar(select(func.count()).select_from(QRPass).where(QRPass.is_on_territory == True))
    return count
