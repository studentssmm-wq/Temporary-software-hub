from aiogram import Router, F
from aiogram.types import BufferedInputFile, Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.filters import CommandStart, CommandObject, Command
from app.services.qr_service import create_qr_pass, process_pass_scan
from app.repositories.user_repository import find_user_by_id
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.states.registration_states import Registration
from app.keyboards.main_keyboard import get_main_menu_kb
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
    pass_id_str = command.args

    try:
        pass_id = UUID(pass_id_str)
    except ValueError:
        await message.answer("❌ Недійсний QR-код.")
        return

    # 2. Отримуємо Telegram ID волонтера (того, хто натиснув на посилання / сканував)
    scanner_id = message.from_user.id

    # 3. Передаємо scanner_id у сервіс
    qr_pass, was_on_territory = await process_pass_scan(
        session=session,
        pass_id=pass_id,
        scanner_id=scanner_id  # 👈 Додано цей параметр
    )

    # 4. Виводимо результат сканування
    if not qr_pass:
        await message.answer("❌ Перепустку не знайдено в базі!")
        return

    if was_on_territory:
        await message.answer("✅ <b>Успішно!</b>\nСтудент <b>вийшов</b> з локації.", parse_mode="HTML")
    else:
        await message.answer("✅ <b>Успішно!</b>\nСтудент <b>зайшов</b> на локацію.", parse_mode="HTML")


@qr_router.message(CommandStart())
async def start_handler(message: Message, session: AsyncSession, state: FSMContext):
    user = await find_user_by_id(session, message.from_user.id)

    if user:
        await message.answer(
            f"З поверненням, {user.first_name}! 👋\nОберіть потрібну дію нижче:",
            reply_markup=get_main_menu_kb(user.user_role)
        )
    else:
        await state.update_data(
            telegram_id=message.from_user.id,
            telegram_tag=message.from_user.username
        )
        await message.answer(
            "Привіт! Ти ще не зареєстрований.\nПочинаємо реєстрацію. Будь ласка, введи свій ПІБ (Прізвище та Ім'я):",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(Registration.full_name)


@qr_router.callback_query(F.data == "main_qr")
async def main_qr_callback(callback: CallbackQuery, session: AsyncSession):
    pass_id, qr_file = await create_qr_pass(session, callback.from_user.id)
    photo = BufferedInputFile(
        qr_file.getvalue(),
        filename=f"{pass_id}.png"
    )

    await callback.message.answer_photo(photo=photo, caption="Ось ваша QR-перепустка!")
    await callback.answer()
