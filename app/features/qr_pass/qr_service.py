from io import BytesIO
from uuid import UUID, uuid4

import segno
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.qr_pass.qr_repository import (
    create_pass,
    get_pass_id_by_user,
    toggle_pass,
)
from app.features.users.user_repository import find_user_by_id


def generate_qr(pass_id: UUID, bot_username: str) -> bytes:
    if not bot_username:
        raise ValueError("Bot username is required")

    qrcode = segno.make(f"https://t.me/{bot_username}?start={pass_id}")
    with BytesIO() as qr_file:
        qrcode.save(qr_file, kind="png", scale=10)
        return qr_file.getvalue()


async def create_qr_pass(
    session: AsyncSession,
    telegram_id: int,
    bot_username: str,
) -> tuple[UUID, bytes] | None:
    if not bot_username:
        raise ValueError("Bot username is required")

    pass_id = await get_pass_id_by_user(session, telegram_id)

    if pass_id is None:
        user = await find_user_by_id(session, telegram_id)
        if not user:
            return None
        pass_id = await create_pass(session, uuid4(), telegram_id)

    return pass_id, generate_qr(pass_id, bot_username)


async def process_pass_scan(
    session: AsyncSession,
    pass_id: UUID,
    scanner_id: int,
) -> bool | None:
    scanner = await find_user_by_id(session, scanner_id)
    if not scanner or scanner.user_role not in ("admin", "volunteer"):
        raise PermissionError("Only admins and volunteers can scan passes")

    return await toggle_pass(session, pass_id, scanner_id)
