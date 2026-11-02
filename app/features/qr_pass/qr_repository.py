from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import QRPass, ScanLog


async def get_pass_id_by_user(
    session: AsyncSession,
    telegram_id: int,
) -> UUID | None:

    result = await session.execute(
        select(QRPass.pass_id).where(QRPass.telegram_id == telegram_id)
    )

    return result.scalar_one_or_none()


async def create_pass(
    session: AsyncSession,
    pass_id: UUID,
    telegram_id: int,
) -> UUID:

    try:
        result = await session.execute(
            insert(QRPass)
            .values(
                pass_id=pass_id,
                telegram_id=telegram_id,
                is_on_territory=False,
            )
            .on_conflict_do_nothing(index_elements=[QRPass.telegram_id])
            .returning(QRPass.pass_id)
        )
        created_pass_id = result.scalar_one_or_none()

        if created_pass_id is None:
            result = await session.execute(
                select(QRPass.pass_id).where(QRPass.telegram_id == telegram_id)
            )
            created_pass_id = result.scalar_one()

        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise

    return created_pass_id


async def toggle_pass(
    session: AsyncSession,
    pass_id: UUID,
    scanner_id: int,
) -> bool | None:

    try:
        result = await session.execute(
            update(QRPass)
            .where(QRPass.pass_id == pass_id)
            .values(is_on_territory=~QRPass.is_on_territory)
            .returning(QRPass.telegram_id, QRPass.is_on_territory)
            .execution_options(synchronize_session=False)
        )
        row = result.first()

        if row is None:
            return None

        session.add(
            ScanLog(
                telegram_id=row.telegram_id,
                scanner_id=scanner_id,
                action_type="in" if row.is_on_territory else "out",
                scanned_at=datetime.now(ZoneInfo("Europe/Kyiv")),
            )
        )

        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise

    return row.is_on_territory
