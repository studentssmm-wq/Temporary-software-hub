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
        InlineKeyboardButton(text="🔙 Назад до головного меню",
                             callback_data="back_to_main")
    )

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
