from aiogram import Router
from aiogram.types import BufferedInputFile, Message
from aiogram.filters import CommandStart, CommandObject, Command
from app.services.qr_service import create_qr_pass, toggle_pass
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
qr = Router()


@qr.message(Command("qr"))
async def generate_qr_handler(session: AsyncSession, message: Message):
    pass_id, qr_file = await create_qr_pass(session, message.from_user.id)

    photo = BufferedInputFile(
        qr_file.getvalue(),
        filename=f"{pass_id}.png"
    )
    await message.answer_photo(photo=photo, caption="Ваш QR-пропуск створено")


@qr.message(CommandStart(deep_link=True))
async def process_qr(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
):
    pass_id = UUID(command.args)

    qr_pass = await toggle_pass(
        session,
        pass_id,
    )

    if qr_pass is None:
        await message.answer("Пропуск не знайдено")
        return

    if qr_pass.is_on_territory:
        await message.answer("Вихід зафіксовано")
    else:
        await message.answer("Вхід зафіксовано")
