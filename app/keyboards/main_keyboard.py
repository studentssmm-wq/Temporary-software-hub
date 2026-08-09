from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu_kb(role: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="📲 Мій QR-код", callback_data="main_qr")
    builder.button(text="👤 Мій профіль", callback_data="main_profile")

    if role == "admin":
        builder.button(text="👑 Адмін-панель", callback_data="main_admin")

    builder.adjust(1)

    return builder.as_markup()
