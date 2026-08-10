from aiogram import Router, F
from aiogram.types import BufferedInputFile, Message, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InputMediaPhoto
from aiogram.filters import CommandStart, CommandObject, Command
from app.services.qr_service import create_qr_pass, process_pass_scan
from app.repositories.user_repository import find_user_by_id
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.states.registration_states import Registration
from app.keyboards.main_keyboard import (get_main_menu_kb, get_start_menu_kb,
                                         get_schedule_days_user_kb, get_schedule_pagination_kb)
from app.repositories.media_repository import get_media
from app.repositories.schedule_repository import get_schedule_days, get_schedule_photos_by_day
qr_router = Router()


@qr_router.message(Command("qr"))
async def generate_qr_handler(message: Message, session: AsyncSession):
    pass_id, qr_file = await create_qr_pass(session, message.from_user.id)

    photo = BufferedInputFile(
        qr_file.getvalue(),
        filename=f"{pass_id}.png"
    )
    await message.answer_photo(photo=photo, caption="Ваш QR-пропуск створено")


@qr_router.message(Command("menu"))
async def menu_command_handler(message: Message, session: AsyncSession):
    """Обробник команди /menu"""
    user = await find_user_by_id(session, message.from_user.id)

    if user:
        await message.answer(
            "📋 Головне меню:\nОберіть потрібний розділ:",
            reply_markup=get_main_menu_kb(user.user_role)
        )
    else:
        await message.answer("❌ Ви ще не зареєстровані. Натисніть /start для реєстрації.")


@qr_router.callback_query(F.data == "event_map")
async def event_map_handler(callback: CallbackQuery, session: AsyncSession):
    file_id = await get_media(session, "map")

    if not file_id:
        await callback.answer("❌ Мапу ще не завантажено адміністратором.", show_alert=True)
        return

    await callback.message.answer_photo(
        photo=file_id,
        caption="🗺 Ось мапа наших подій!"
    )
    await callback.answer()


@qr_router.callback_query(F.data == "event_schedule")
async def event_schedule_handler(callback: CallbackQuery, session: AsyncSession):
    days = await get_schedule_days(session)

    if not days:
        await callback.answer("❌ Розкладів ще немає.", show_alert=True)
        return

    # Важливий нюанс: Telegram не дозволяє просто змінити текст на фото.
    # Тому ми видаляємо попереднє повідомлення і надсилаємо нове.
    await callback.message.delete()
    await callback.message.answer(
        "📅 Оберіть день, розклад якого хочете переглянути:",
        reply_markup=get_schedule_days_user_kb(days)
    )
    await callback.answer()


@qr_router.callback_query(F.data.startswith("show_day_"))
async def show_schedule_day_handler(callback: CallbackQuery, session: AsyncSession):
    day = int(callback.data.replace("show_day_", ""))
    photos = await get_schedule_photos_by_day(session, day)

    if not photos:
        await callback.answer("❌ Фотографій не знайдено.", show_alert=True)
        return

    # Знову видаляємо текстове повідомлення і надсилаємо фотографію (першу в списку, index=0)
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photos[0],
        caption=f"📅 Розклад на {day} число",
        parse_mode="HTML",
        reply_markup=get_schedule_pagination_kb(day, 0, len(photos))
    )
    await callback.answer()


@qr_router.callback_query(F.data.startswith("sched_page_"))
async def schedule_pagination_handler(callback: CallbackQuery, session: AsyncSession):
    # Витягуємо день та індекс з callback_data (наприклад, sched_page_25_1)
    _, _, day_str, index_str = callback.data.split("_")
    day, index = int(day_str), int(index_str)

    photos = await get_schedule_photos_by_day(session, day)

    # Використовуємо edit_media для плавної заміни картинки без надсилання нового повідомлення
    media = InputMediaPhoto(
        media=photos[index],
        caption=f"📅 Розклад на {day} число",
        parse_mode="HTML"
    )

    await callback.message.edit_media(
        media=media,
        reply_markup=get_schedule_pagination_kb(day, index, len(photos))
    )
    await callback.answer()


@qr_router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    # Це порожній обробник для кнопки-лічильника "1 / 3", щоб вона не видавала помилок при натисканні
    await callback.answer()


@qr_router.callback_query(F.data == "main_menu")
async def main_menu_callback_handler(callback: CallbackQuery, session: AsyncSession):
    """Обробник натискання кнопки 'Головне меню'"""
    user = await find_user_by_id(session, callback.from_user.id)

    if user:
        await callback.message.edit_text(
            "📋 Головне меню:\nОберіть потрібний розділ:",
            reply_markup=get_main_menu_kb(user.user_role)
        )
    else:
        await callback.message.answer("❌ Ви ще не зареєстровані. Натисніть /start для реєстрації.")

    await callback.answer()


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
            reply_markup=get_start_menu_kb(user.user_role)  # <--- ОСЬ ТУТ ЗМІНА
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
