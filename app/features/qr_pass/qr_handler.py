<<<<<<< HEAD
import asyncio
from aiogram import Router, F
from aiogram.types import BufferedInputFile, Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto
from aiogram.filters import CommandStart, CommandObject, Command
from app.features.qr_pass.qr_service import create_qr_pass, process_pass_scan
from app.features.users.user_repository import find_user_by_id
from sqlalchemy.ext.asyncio import AsyncSession
=======
>>>>>>> dc546faa8424b97c30a665e0af90dad5f4fc7a83
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.qr_pass.qr_service import create_qr_pass, process_pass_scan

qr_router = Router()

<<<<<<< HEAD
_SCAN_REPLY_INTERVAL = 1.1
_scan_reply_locks: dict[int, asyncio.Lock] = {}
_last_scan_reply_at: dict[int, float] = {}


async def _answer_scan_message(
    message: Message,
    text: str,
    *,
    parse_mode: str | None = None,
) -> None:
    scanner_id = message.chat.id
    lock = _scan_reply_locks.setdefault(scanner_id, asyncio.Lock())

    async with lock:
        loop = asyncio.get_running_loop()
        elapsed = loop.time() - _last_scan_reply_at.get(scanner_id, 0)
        if elapsed < _SCAN_REPLY_INTERVAL:
            await asyncio.sleep(_SCAN_REPLY_INTERVAL - elapsed)

        await message.answer(text, parse_mode=parse_mode)
        _last_scan_reply_at[scanner_id] = loop.time()
=======
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
>>>>>>> dc546faa8424b97c30a665e0af90dad5f4fc7a83


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

<<<<<<< HEAD
    # 2. ПЕРЕВІРКА ПРАВ: Шукаємо сканера в базі та перевіряємо роль
    scanner_user = await find_user_by_id(session, scanner_id)
    
    if not scanner_user or scanner_user.user_role not in ["admin", "volunteer"]:
        await _answer_scan_message(message, "❌ У вас немає прав для сканування перепусток!")
        return # Зупиняємо виконання, якщо це звичайний юзер або незареєстрований

    # 3. Обробка самого QR-коду (якщо перевірка пройдена)
    pass_id_str = command.args
=======
    if not command.args:
        await message.answer("❌ Недійсний формат QR-коду.")
        return
>>>>>>> dc546faa8424b97c30a665e0af90dad5f4fc7a83

    try:
        pass_id = UUID(command.args)
    except ValueError:
        await _answer_scan_message(message, "❌ Недійсний формат QR-коду.")
        return

    try:
        is_on_territory = await process_pass_scan(
            session=session, pass_id=pass_id, scanner_id=message.from_user.id
        )
    except PermissionError:
        await message.answer("❌ У вас немає прав для сканування перепусток!")
        return

<<<<<<< HEAD
    # 5. Виводимо результат сканування
    if not qr_pass:
        await _answer_scan_message(message, "❌ Перепустку не знайдено в базі!")
        return

    if was_on_territory:
        await _answer_scan_message(
            message,
            "✅ <b>Успішно!</b>\nСтудент <b>вийшов</b> з локації.",
            parse_mode="HTML",
        )
    else:
        await _answer_scan_message(
            message,
            "✅ <b>Успішно!</b>\nСтудент <b>зайшов</b> на локацію.",
            parse_mode="HTML",
        )


@qr_router.message(CommandStart())
async def start_handler(message: Message, session: AsyncSession, state: FSMContext):
    user = await find_user_by_id(session, message.from_user.id)

    if user:
=======
    if is_on_territory is None:
        await message.answer("❌ Перепустку не знайдено в базі!")
        return

    if is_on_territory:
>>>>>>> dc546faa8424b97c30a665e0af90dad5f4fc7a83
        await message.answer(
            "✅ <b>Успішно!</b>\nСтудент <b>зайшов</b> на локацію.", parse_mode="HTML"
        )
    else:
        await message.answer(
            "✅ <b>Успішно!</b>\nСтудент <b>вийшов</b> з локації.", parse_mode="HTML"
        )
