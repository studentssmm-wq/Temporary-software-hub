from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import QRPass, ScanLog


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
    scanner_id: int,  # 👈 Додаємо ID сканера
) -> QRPass:

    qr_pass.is_on_territory = not qr_pass.is_on_territory

    # 👈 Визначаємо тип дії (зайшов чи вийшов)
    action = "in" if qr_pass.is_on_territory else "out"

    # 👈 Створюємо запис для статистики
    scan_log = ScanLog(
        telegram_id=qr_pass.telegram_id,
        scanner_id=scanner_id,
        action_type=action
    )
    session.add(scan_log)  # Додаємо лог у сесію

    await session.commit()
    await session.refresh(qr_pass)

    return qr_pass
