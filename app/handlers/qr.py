from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart, CommandObject

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        f"Привіт, {message.from_user.first_name}! 👋"
    )


@router.message(CommandStart(deep_link=True))
async def scan_qr_handler(message: Message, command: CommandObject):
    scanned_uuid = command.args
    await message.answer(f"UUID: {scanned_uuid}")
