import uuid
from io import BytesIO
import segno

from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.qr import create_pass, get_pass_by_user


def generate_pass_id() -> uuid.UUID:
    return uuid.uuid4()


def generate_qr(pass_id: uuid.UUID) -> BytesIO:
    deep_link = (
        f"https://t.me/students_nulp_official_bot"
        f"?start={pass_id}"
    )

    qrcode = segno.make(deep_link)
    qr_file = BytesIO()
    qrcode.save(qr_file, kind="png", scale=10)
    qr_file.seek(0)
    return qr_file


async def create_qr_pass(session: AsyncSession, telegram_id: int):
    existing_pass = await get_pass_by_user(session, telegram_id)
    if existing_pass:
        pass_id = existing_pass.pass_id
        qrcode = generate_qr(pass_id)

        return pass_id, qrcode

    pass_id = generate_pass_id()

    await create_pass(
        session,
        pass_id,
        telegram_id,
    )
    qrcode = generate_qr(pass_id)

    return pass_id, qrcode


async def get_pass(pass_id):
    pass


async def toggle_pass(pass_id):
    pass
