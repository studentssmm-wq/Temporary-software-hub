from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_admin_main_kb() -> InlineKeyboardMarkup:
    """Головне меню адміністратора"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")
    )
    builder.row(
        InlineKeyboardButton(text="👑 Призначити Адміна",
                             callback_data="admin_assign_admin"),
        InlineKeyboardButton(text="🤝 Призначити Волонтера",
                             callback_data="admin_assign_volunteer")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Зробити оголошення",
                             callback_data="admin_broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="🗺 Оновити мапу подій", callback_data="admin_update_map")
    )
    builder.row(
        InlineKeyboardButton(text="📅 Керування розкладом", callback_data="admin_schedule_menu")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад до головного меню",
                             callback_data="back_to_main")
    )


    return builder.as_markup()


def get_schedule_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Додати розклад", callback_data="schedule_add"))
    builder.row(InlineKeyboardButton(text="🗑 Видалити розклад", callback_data="schedule_delete"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_admin"))
    return builder.as_markup()


def get_finish_upload_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Завершити завантаження", callback_data="schedule_finish"))
    return builder.as_markup()


def get_days_for_delete_kb(days: list[int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for d in days:
        # Тепер ми передаємо просто число
        builder.button(text=f"{d} число", callback_data=f"del_sched_{d}")

    builder.adjust(3)  # По 3 кнопки в ряд, бо вони тепер коротші
    builder.row(InlineKeyboardButton(text="🔙 Скасувати", callback_data="admin_schedule_menu"))
    return builder.as_markup()

def get_broadcast_target_kb() -> InlineKeyboardMarkup:
    """Клавіатура для вибору аудиторії розсилки"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📍 Тільки тим, хто на території", callback_data="broadcast_on")
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Тільки тим, хто поза територією", callback_data="broadcast_off")
    )
    builder.row(
        InlineKeyboardButton(text="🌐 Абсолютно всім",
                             callback_data="broadcast_all")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Скасувати", callback_data="admin_cancel")
    )

    return builder.as_markup()
