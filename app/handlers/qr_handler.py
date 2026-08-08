from aiogram import Router
from aiogram.types import BufferedInputFile, Message
from aiogram.filters import CommandStart, CommandObject, Command
from app.services.qr_service import create_qr_pass, process_pass_scan
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
qr_router = Router()


@qr_router.message(Command("qr"))
async def generate_qr_handler(message: Message, session: AsyncSession):
    pass_id, qr_file = await create_qr_pass(session, message.from_user.id)

    photo = BufferedInputFile(
        qr_file.getvalue(),
        filename=f"{pass_id}.png"
    )
    await message.answer_photo(photo=photo, caption="Ваш QR-пропуск створено")


@qr_router.message(CommandStart(deep_link=True))
async def scan_qr(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
):
    try:
        pass_id = UUID(command.args)
    except (ValueError, TypeError):
        await message.answer(
            "❌ Некоректний QR-код."
        )
        return

    qr_pass, was_on_territory = await process_pass_scan(
        session,
        pass_id,
    )

    if qr_pass is None:
        await message.answer(
            "❌ Пропуск не знайдено."
        )
        return

    if was_on_territory:
        await message.answer(
            "🚪 Вихід зафіксовано."
        )
    else:
        await message.answer(
            "✅ Вхід зафіксовано."
        )


@qr_router.message(CommandStart())
async def start_handler(message: Message):
    await message.answer(
        f"Привіт, {message.from_user.first_name}! 👋"
    )
