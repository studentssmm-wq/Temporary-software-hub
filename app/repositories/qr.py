from uuid import UUID

from sqlalchemy import select, delete, func

from app.database.models import QRPass
from sqlalchemy.ext.asyncio import AsyncSession


async def delete_duplicate_passes(session: AsyncSession):
    result = await session.execute(
        select(QRPass.telegram_id)
        .group_by(QRPass.telegram_id)
        .having(func.count(QRPass.pass_id) > 1)
    )

    duplicate_users = result.scalars().all()

    deleted_count = 0

    for telegram_id in duplicate_users:
        result = await session.execute(
            select(QRPass)
            .where(QRPass.telegram_id == telegram_id)
            .order_by(QRPass.pass_id)
        )

        passes = result.scalars().all()

        # залишаємо перший
        for qr_pass in passes[1:]:
            await session.delete(qr_pass)
            deleted_count += 1

    await session.commit()

    return deleted_count


async def get_pass(session, pass_id: UUID):
    result = await session.execute(
        select(QRPass).where(QRPass.pass_id == pass_id)
    )

    return result.scalar_one_or_none()


async def get_pass_by_user(session: AsyncSession, telegram_id: int,) -> QRPass | None:
    result = await session.execute(
        select(QRPass).where(
            QRPass.telegram_id == telegram_id
        )
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
