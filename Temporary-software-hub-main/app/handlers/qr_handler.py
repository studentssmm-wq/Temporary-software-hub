from uuid import UUID

from aiogram import Router
from aiogram.types import BufferedInputFile, Message
from aiogram.filters import CommandStart, CommandObject, Command
from sqlalchemy.ext.asyncio import AsyncSession

# Імпортуємо твій ідеальний сервіс
from app.services.qr_service import create_qr_pass, process_pass_scan
from app.database.user import User

qr = Router()

@qr.message(Command("qr"))
async def generate_qr_handler(message: Message, session: AsyncSession):
    # 1. Захист: перевіряємо, чи людина взагалі пройшла реєстрацію (є в таблиці users)
    user = await session.get(User, message.from_user.id)
    if not user:
        await message.answer("❌ Спочатку потрібно зареєструватися! Натисни /start")
        return

    # 2. Викликаємо твій сервіс. Він сам розбереться: 
    # якщо пропуск вже є — просто видасть картинку, якщо ні — створить у базі.
    pass_id, qr_file = await create_qr_pass(session, message.from_user.id)

    photo = BufferedInputFile(
        qr_file.getvalue(),
        filename=f"{pass_id}.png"
    )
    await message.answer_photo(photo=photo, caption="Твій QR-пропуск 🎫")


@qr.message(CommandStart(deep_link=True))
async def scan_qr(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
):
    try:
        pass_id = UUID(command.args)
    except (ValueError, TypeError):
        await message.answer("❌ Некоректний QR-код.")
        return

    qr_pass, was_on_territory = await process_pass_scan(
        session,
        pass_id,
    )

    if qr_pass is None:
        await message.answer("❌ Пропуск не знайдено.")
        return

    if was_on_territory:
        await message.answer("🚪 Вихід зафіксовано.")
    else:
        await message.answer("✅ Вхід зафіксовано.")