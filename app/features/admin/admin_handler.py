import re
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.context import FSMContext
from app.shared.admin_filter import AdminFilter
from app.features.admin.admin_keyboard import (get_admin_main_kb, get_broadcast_target_kb,
                                               get_schedule_menu_kb, get_finish_upload_kb, get_days_for_delete_kb,
                                               get_broadcast_type_kb, get_broadcast_date_kb)
from app.shared.main_keyboard import get_main_menu_kb
from app.features.analytics.statistics_keyboard import get_statistics_main_kb
from app.features.users.user_repository import update_user_role, get_users_for_broadcast

from app.features.admin.admin_states import AdminRoleState, BroadcastState, MediaUpdateState, ScheduleUpdateState
from app.features.mailing.media_repository import update_media
from datetime import datetime, timedelta, timezone
from app.features.mailing.schedule_repository import add_schedule_photo, get_schedule_days, delete_schedule_for_day
from app.core.models import ScheduledMailing
from sqlalchemy import select, delete
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.features.payments.coin_service import process_coin_transaction
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

    await callback.message.edit_text(
        "Оберіть тип звіту:",
        reply_markup=get_statistics_main_kb()
    )
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
async def broadcast_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastState.waiting_for_type)
    await callback.message.edit_text(
        "📢 Коли бажаєте зробити розсилку?",
        reply_markup=get_broadcast_type_kb()
    )
    await callback.answer()


@admin_router.callback_query(BroadcastState.waiting_for_type, F.data.in_(["bcast_type_now", "bcast_type_scheduled"]))
async def process_broadcast_type(callback: CallbackQuery, state: FSMContext):
    bcast_type = "now" if callback.data == "bcast_type_now" else "scheduled"
    await state.update_data(bcast_type=bcast_type)

    if bcast_type == "now":
        await state.set_state(BroadcastState.waiting_for_filter)
        await callback.message.edit_text(
            "📢 Оберіть аудиторію для розсилки:",
            reply_markup=get_broadcast_target_kb()
        )
    else:
        await state.set_state(BroadcastState.waiting_for_date)
        await callback.message.edit_text(
            "📅 Оберіть дату розсилки на клавіатурі\nабо <b>введіть вручну у форматі ДД.ММ.РРРР:</b>",
            reply_markup=get_broadcast_date_kb(),
            parse_mode="HTML"
        )
    await callback.answer()


@admin_router.callback_query(BroadcastState.waiting_for_date, F.data.startswith("bcast_date_"))
async def process_broadcast_date(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split("_")[2]
    await state.update_data(bcast_date=date_str)
    await state.set_state(BroadcastState.waiting_for_time)

    cancel_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Скасувати", callback_data="admin_cancel")]])
    await callback.message.edit_text(
        f"📅 Обрано дату: {date_str}\n\n"
        "✍️ Тепер введіть час для розсилки у форматі ГГ:ХХ (наприклад 14:30):",
        parse_mode="HTML",
        reply_markup=cancel_kb
    )
    await callback.answer()


@admin_router.message(BroadcastState.waiting_for_time)
async def process_broadcast_time(message: Message, state: FSMContext):
    time_text = message.text.strip()

    if not re.match(r"^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$", time_text):
        await message.answer("⚠️ Неправильний формат часу. Будь ласка, введіть час у форматі ГГ:ХХ (наприклад, 14:30):")
        return

    await state.update_data(bcast_time=time_text)
    await state.set_state(BroadcastState.waiting_for_filter)

    await message.answer(
        f"🕒 Час встановлено: {time_text}\n\n"
        "📢 Оберіть аудиторію для розсилки:",
        parse_mode="HTML",
        reply_markup=get_broadcast_target_kb()
    )


@admin_router.callback_query(BroadcastState.waiting_for_filter,
                             F.data.in_(["broadcast_on", "broadcast_off", "broadcast_all"]))
async def ask_broadcast_message(callback: CallbackQuery, state: FSMContext):
    target = callback.data.split("_")[1]
    await state.update_data(target=target)
    await state.set_state(BroadcastState.waiting_for_message)

    cancel_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Скасувати", callback_data="admin_cancel")]])
    await callback.message.edit_text(
        "✍️ Надішліть текст оголошення (можна форматувати текст, додавати фото/відео):",
        parse_mode="HTML",
        reply_markup=cancel_kb
    )
    await callback.answer()


@admin_router.message(BroadcastState.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    target = data.get("target")
    bcast_type = data.get("bcast_type")

    if bcast_type == "now":
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
            f"✅ Розсилку завершено!\n\n"
            f"📩 Успішно доставлено: {success_count}\n"
            f"❌ Помилок (заблоковано): {fail_count}",
            parse_mode="HTML"
        )
    else:
        bcast_date = data.get("bcast_date")
        bcast_time = data.get("bcast_time")

        current_year = datetime.now().year
        date_time_str = f"{bcast_date}.{current_year} {bcast_time}"

        kyiv_tz = timezone(timedelta(hours=3))
        send_at = datetime.strptime(
            date_time_str, "%d.%m.%Y %H:%M").replace(tzinfo=kyiv_tz)

        media_type = None
        media_file_id = None
        text = message.text or message.caption

        if message.photo:
            media_type = "photo"
            media_file_id = message.photo[-1].file_id
        elif message.video:
            media_type = "video"
            media_file_id = message.video.file_id
        elif message.document:
            media_type = "document"
            media_file_id = message.document.file_id

        new_mailing = ScheduledMailing(
            message_text=text,
            media_file_id=media_file_id,
            media_type=media_type,
            audience=target,
            send_at=send_at,
            status="pending"
        )
        session.add(new_mailing)
        await session.commit()

        await message.answer(
            f"✅ Розсилку успішно заплановано!\n\n"
            f"📅 Дата: {bcast_date}\n"
            f"🕒 Час: {bcast_time}\n"
            f"👥 Аудиторія: {target}\n\n"
            "Очікуйте, бот розішле її автоматично.",
            parse_mode="HTML"
        )

    await state.clear()


@admin_router.message(BroadcastState.waiting_for_date)
async def process_manual_date_input(message: Message, state: FSMContext):
    try:
        parsed_date = datetime.strptime(message.text.strip(), "%d.%m.%Y")
        formatted_date = parsed_date.strftime("%d.%m")

        await state.update_data(bcast_date=formatted_date)
        await state.set_state(BroadcastState.waiting_for_time)

        cancel_kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(
                text="🔙 Скасувати", callback_data="admin_cancel")]]
        )

        await message.answer(
            f"📅 Обрано дату: {formatted_date}\n\n"
            "✍️ Тепер введіть час для розсилки у форматі ГГ:ХХ (наприклад: 14:30):",
            reply_markup=cancel_kb
        )
    except ValueError:
        await message.answer(
            "❌ Неправильний формат дати.\n\n"
            "Будь ласка, введіть дату у форматі <b>ДД.ММ.РРРР</b> (наприклад: 25.09.2026) або оберіть на клавіатурі.",
            parse_mode="HTML"
        )


@admin_router.callback_query(F.data == "scheduled_list")
async def show_scheduled_mailings(callback: CallbackQuery, session: AsyncSession):
    result = await session.execute(
        select(ScheduledMailing).where(ScheduledMailing.status == "pending")
    )
    mailings = result.scalars().all()

    if not mailings:
        await callback.message.edit_text(
            "📭 Немає запланованих розсилок.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_broadcast")]])
        )
        return await callback.answer()

    builder = InlineKeyboardBuilder()

    for m in mailings:
        text_preview = m.message_text if m.message_text else "[Медіа]"
        short_text = text_preview[:15] + \
            "..." if len(text_preview) > 15 else text_preview
        time_str = m.send_at.strftime("%d.%m %H:%M")

        builder.button(text=f"🗑 {time_str} | {short_text}",
                       callback_data=f"del_mail_{m.id}")

    builder.button(text="🔙 Назад", callback_data="admin_broadcast")
    builder.adjust(1)

    await callback.message.edit_text(
        "🗓 <b>Заплановані розсилки</b>\n\nНатисніть на розсилку, щоб скасувати її:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("del_mail_"))
async def delete_scheduled_mailing(callback: CallbackQuery, session: AsyncSession):
    mailing_id = int(callback.data.split("_")[2])
    await session.execute(
        delete(ScheduledMailing).where(ScheduledMailing.id == mailing_id)
    )
    await session.commit()
    await callback.answer("✅ Розсилку успішно скасовано!", show_alert=True)
    await show_scheduled_mailings(callback, session)


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
        [InlineKeyboardButton(text="🔙 Скасувати",
                              callback_data="admin_cancel")]
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
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
            text="🔙 Скасувати", callback_data="admin_schedule_menu")]])
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
