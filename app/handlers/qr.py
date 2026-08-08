from aiogram import Router
from aiogram.types import BufferedInputFile, Message
from aiogram.filters import CommandStart, CommandObject, Command
from app.database.database import session_factory
from app.services.qr_service import create_qr_pass

qr = Router()


@qr.message(Command("qr"))
async def generate_qr_handler(message: Message):
    async with session_factory() as session:
        pass_id, qr_file = await create_qr_pass(session, message.from_user.id)

    photo = BufferedInputFile(
        qr_file.getvalue(),
        filename=f"{pass_id}.png"
    )
    await message.answer_photo(photo=photo, caption="Ваш QR-пропуск створено")


@qr.message(CommandStart(deep_link=True))
async def scan_qr_handler(message: Message, command: CommandObject):
    scanned_uuid = command.args
    await message.answer(f"UUID: {scanned_uuid}")
