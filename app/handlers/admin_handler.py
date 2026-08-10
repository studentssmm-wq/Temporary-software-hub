import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.context import FSMContext
from app.filters.admin_filter import AdminFilter
from app.keyboards.admin_keyboard import (get_admin_main_kb, get_broadcast_target_kb,
                                          get_schedule_menu_kb, get_finish_upload_kb, get_days_for_delete_kb)
from app.keyboards.main_keyboard import get_main_menu_kb
from app.repositories.qr_repository import get_users_on_territory_count
from app.repositories.user_repository import update_user_role, get_users_for_broadcast

from app.states.admin_states import AdminRoleState, BroadcastState, MediaUpdateState, ScheduleUpdateState
from app.repositories.media_repository import update_media
from datetime import datetime
from app.repositories.schedule_repository import add_schedule_photo, get_schedule_days, delete_schedule_for_day
admin_router = Router()

admin_router.message.filter(AdminFilter())
admin_router.callback_query.filter(AdminFilter())


@admin_router.message(Command("cancel"))
async def cancel_fsm_handler(message: Message, state: FSMContext):
    """Скасовує будь-яку поточну дію FSM"""
    current_state = await state.get_state()
    if current_state is None:
        return  # Якщо стану немає, нічого не робимо

    await state.clear()
    await message.answer("Дію скасовано. Повернення до нормального режиму.", reply_markup=ReplyKeyboardRemove())


@admin_router.message(Command("admin"))
async def admin_panel_handler(message: Message, state: FSMContext):
    await state.clear()  # 👈 Очищаємо стан!
    await message.answer(
        "👋 Вітаю в панелі адміністратора!\n\nОберіть потрібну дію з меню нижче:",
        reply_markup=get_admin_main_kb()
    )


@admin_router.callback_query(F.data == "admin_cancel")
# Додано state
async def cancel_action_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.edit_text(
        "👋 Вітаю в панелі адміністратора!\n\nОберіть потрібну дію з меню нижче:",
        reply_markup=get_admin_main_kb()
    )
    await callback.answer()


@admin_router.callback_query(F.data == "back_to_main")
# Додано state
async def back_to_main_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()

    await callback.message.edit_text(
        "Оберіть потрібну дію нижче:",
        reply_markup=get_main_menu_kb(role="admin")
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_stats")
async def show_stats_handler(callback: CallbackQuery, session: AsyncSession):
    count = await get_users_on_territory_count(session)

    await callback.message.answer(f"📊 Зараз на території перебуває: {count} осіб.")
    await callback.answer()


@admin_router.callback_query(F.data == "admin_assign_admin")
async def assign_admin_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminRoleState.waiting_for_admin_id)
    await callback.message.answer("✍️ Введіть Telegram ID користувача, якого хочете призначити Адміністратором:")
    await callback.answer()


@admin_router.message(AdminRoleState.waiting_for_admin_id)
async def process_admin_id(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text.isdigit():
        await message.answer("⚠️ Помилка! ID має містити лише цифри. Спробуйте ще раз:")
        return

    user_id = int(message.text)

    updated_user = await update_user_role(session, user_id, "admin")

    if updated_user is None:
        await message.answer("❌ Користувача з таким ID не знайдено в базі даних.")
    else:
        await message.answer(f"✅ Успішно! Користувачу {user_id} надано роль Адміністратора.")

    await state.clear()


@admin_router.callback_query(F.data == "admin_assign_volunteer")
async def assign_volunteer_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminRoleState.waiting_for_volunteer_id)
    await callback.message.answer("✍️ Введіть Telegram ID користувача, якого хочете призначити Волонтером:")
    await callback.answer()


@admin_router.message(AdminRoleState.waiting_for_volunteer_id)
async def process_volunteer_id(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text.isdigit():
        await message.answer("⚠️ Помилка! ID має містити лише цифри. Спробуйте ще раз:")
        return

    user_id = int(message.text)

    updated_user = await update_user_role(session, user_id, "volunteer")

    if updated_user is None:
        await message.answer("❌ Користувача з таким ID не знайдено в базі даних.")
    else:
        await message.answer(f"✅ Успішно! Користувачу {user_id} надано роль Волонтера.")

    await state.clear()


@admin_router.callback_query(F.data == "admin_broadcast")
async def broadcast_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "📢 Оберіть аудиторію для розсилки оголошення:",
        reply_markup=get_broadcast_target_kb()
    )
    await callback.answer()


@admin_router.callback_query(F.data.in_(["broadcast_on", "broadcast_off", "broadcast_all"]))
async def ask_broadcast_message(callback: CallbackQuery, state: FSMContext):
    target = callback.data.split("_")[1]

    await state.update_data(target=target)
    await state.set_state(BroadcastState.waiting_for_message)

    # 👈 Створюємо кнопку скасування на льоту
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Скасувати",
                              callback_data="admin_cancel")]
    ])

    await callback.message.edit_text(
        "✍️ Надішліть текст оголошення (можна форматувати текст):",
        parse_mode="HTML",
        reply_markup=cancel_kb  # 👈 Додаємо клавіатуру сюди
    )
    await callback.answer()


@admin_router.message(BroadcastState.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    target = data.get("target")

    users_ids = await get_users_for_broadcast(session, target)
    if not users_ids:
        await message.answer("🤷‍♂️ За обраним критерієм не знайдено жодного користувача.")
        await state.clear()
        return
    status_msg = await message.answer(f"⏳ Розпочинаю розсилку для {len(users_ids)} користувачів...")

    success_count = 0
    fail_count = 0

    for user_id in users_ids:
        try:
            await message.copy_to(chat_id=user_id)
            success_count += 1
        except TelegramAPIError:
            fail_count += 1
        await asyncio.sleep(0.05)

    await status_msg.edit_text(
        f"✅ <b>Розсилку завершено!</b>\n\n"
        f"📩 Успішно доставлено: {success_count}\n"
        f"❌ Помилок (заблоковано): {fail_count}",
        parse_mode="HTML"
    )

    await state.clear()


@admin_router.callback_query(F.data == "main_admin")
async def main_admin_callback(callback: CallbackQuery):
    # Відправляємо меню адміністратора
    await callback.message.edit_text(
        "👋 Вітаю в панелі адміністратора!\n\nОберіть потрібну дію з меню нижче:",
        reply_markup=get_admin_main_kb()
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_update_map")
async def ask_for_map_photo(callback: CallbackQuery, state: FSMContext):
    await state.set_state(MediaUpdateState.waiting_for_map)

    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Скасувати", callback_data="admin_cancel")]
    ])

    await callback.message.edit_text(
        "🖼 Надішліть картинку з новою мапою подій:",
        reply_markup=cancel_kb
    )
    await callback.answer()


@admin_router.message(MediaUpdateState.waiting_for_map, F.photo)
async def process_map_photo(message: Message, state: FSMContext, session: AsyncSession):
    # Telegram генерує кілька розмірів фото, [-1] — це найбільша якість
    file_id = message.photo[-1].file_id

    # Зберігаємо file_id в базу даних під іменем "map"
    await update_media(session, "map", file_id)

    await message.answer("✅ Мапу успішно оновлено!")
    await state.clear()


# --- МЕНЮ КЕРУВАННЯ РОЗКЛАДОМ ---
@admin_router.callback_query(F.data == "admin_schedule_menu")
async def schedule_menu_handler(callback: CallbackQuery):
    await callback.message.edit_text("📅 Керування розкладом\nОберіть дію:",
                                     reply_markup=get_schedule_menu_kb(), parse_mode="HTML")
    await callback.answer()


# --- ДОДАВАННЯ РОЗКЛАДУ ---
@admin_router.callback_query(F.data == "schedule_add")
async def schedule_add_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ScheduleUpdateState.waiting_for_date)
    await callback.message.edit_text(
        "✍️ Введіть число місяця для розкладу (від 1 до 31):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Скасувати", callback_data="admin_schedule_menu")]])
    )
    await callback.answer()


@admin_router.message(ScheduleUpdateState.waiting_for_date)
async def schedule_process_day(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Будь ласка, введіть лише число:")
        return

    event_day = int(message.text)

    if event_day < 1 or event_day > 31:
        await message.answer("❌ Число має бути від 1 до 31:")
        return

    await state.update_data(event_day=event_day)
    await state.set_state(ScheduleUpdateState.waiting_for_photos)

    await message.answer(
        f"📅 Обрано: {event_day} число\n\n"
        "🖼 Відправляйте фотографії розкладу (можна альбомом). "
        "Коли надішлете всі — натисніть кнопку нижче.",
        parse_mode="HTML",
        reply_markup=get_finish_upload_kb()
    )


@admin_router.message(ScheduleUpdateState.waiting_for_photos, F.photo)
async def schedule_process_photo(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    event_day = data["event_day"]
    file_id = message.photo[-1].file_id

    await add_schedule_photo(session, event_day, file_id)


@admin_router.callback_query(ScheduleUpdateState.waiting_for_photos, F.data == "schedule_finish")
async def schedule_finish_upload(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("✅ Всі фотографії розкладу успішно збережено!")
    await callback.answer()


# --- ВИДАЛЕННЯ РОЗКЛАДУ ---
@admin_router.callback_query(F.data == "schedule_delete")
async def schedule_delete_start(callback: CallbackQuery, session: AsyncSession):
    days = await get_schedule_days(session)
    if not days:
        await callback.message.edit_text("🤷‍♂️ Розкладів ще немає.",
                                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_schedule_menu")]]))
        return

    await callback.message.edit_text("🗑 Оберіть день, розклад для якого хочете видалити:",
                                     reply_markup=get_days_for_delete_kb(days))
    await callback.answer()


@admin_router.callback_query(F.data.startswith("del_sched_"))
async def schedule_delete_process(callback: CallbackQuery, session: AsyncSession):
    # Отримуємо число з callback_data (наприклад, з 'del_sched_4' дістаємо 4)
    event_day = int(callback.data.replace("del_sched_", ""))

    # Видаляємо розклад для цього дня
    await delete_schedule_for_day(session, event_day)

    # Оновлюємо повідомлення
    await callback.message.edit_text(f"✅ Розклад на {event_day} число повністю видалено!")
    await callback.answer()