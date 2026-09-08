from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.qr_pass.qr_service import create_qr_pass, process_pass_scan

qr_router = Router()

NOT_REGISTERED_TEXT = "❌ Ви ще не зареєстровані. Натисніть /start для реєстрації."


async def send_qr_pass(
    message: Message,
    session: AsyncSession,
    telegram_id: int,
) -> bool:
    bot_username = (await message.bot.me()).username
    if not bot_username:
        raise ValueError("Bot username is required")

    result = await create_qr_pass(session, telegram_id, bot_username)
    if result is None:
        return False

    pass_id, qr_png = result
    await message.answer_photo(
        photo=BufferedInputFile(qr_png, filename=f"{pass_id}.png"),
        caption="Ось ваша QR-перепустка!",
    )
    return True


@qr_router.message(Command("qr"))
async def generate_qr_handler(message: Message, session: AsyncSession):
    if message.from_user is None:
        return

    if not await send_qr_pass(message, session, message.from_user.id):
        await message.answer(NOT_REGISTERED_TEXT)


@qr_router.callback_query(F.data == "main_qr")
async def main_qr_callback(callback: CallbackQuery, session: AsyncSession):
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    if not await send_qr_pass(callback.message, session, callback.from_user.id):
        await callback.answer(NOT_REGISTERED_TEXT, show_alert=True)
        return

    await callback.answer()


@qr_router.message(CommandStart(deep_link=True))
async def scan_qr(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
):
    if message.from_user is None:
        return

    if not command.args:
        await message.answer("❌ Недійсний формат QR-коду.")
        return

    try:
        pass_id = UUID(command.args)
    except ValueError:
        await message.answer("❌ Недійсний формат QR-коду.")
        return

    try:
        is_on_territory = await process_pass_scan(
            session=session, pass_id=pass_id, scanner_id=message.from_user.id
        )
    except PermissionError:
        await message.answer("❌ У вас немає прав для сканування перепусток!")
        return

    if is_on_territory is None:
        await message.answer("❌ Перепустку не знайдено в базі!")
        return

    if is_on_territory:
        await message.answer(
            "✅ <b>Успішно!</b>\nСтудент <b>зайшов</b> на локацію.", parse_mode="HTML"
        )
    else:
        await message.answer(
            "✅ <b>Успішно!</b>\nСтудент <b>вийшов</b> з локації.", parse_mode="HTML"
        )
