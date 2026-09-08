
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu_kb(role: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="📲 Мій QR-код", callback_data="main_qr")
    builder.button(text="🗺 Мапа подій", callback_data="event_map")
    builder.button(text="📅 Розклад подій", callback_data="event_schedule")
    builder.button(text="🤝 Зустріч із адміністрацією", callback_data="admin_meeting_view")
    builder.button(text="📖 Пісенник", callback_data="user_songs_menu")
    builder.button(text="👤 Мій профіль", callback_data="main_profile")
    builder.row(
        InlineKeyboardButton(text="📜 Правила заходу", callback_data="event_rules")
    )
    builder.row(
        InlineKeyboardButton(text="🛡 Укриття", callback_data="event_shelter"),
        InlineKeyboardButton(text="🧘‍♀️ Локація стретчингу", callback_data="event_stretching")
    )
    builder.button(
        text="📝 Реєстрація на стретчинг", 
        url="https://docs.google.com/forms/d/e/1FAIpQLSfa0hyj5JNJ21O1Hjq4Mz-yHeboymOOL__lNA1WvWFYoHmU3g/viewform" 
    )
    builder.button(
        text="🎮 Ігровий Хаб",
        web_app=WebAppInfo(url="https://fortunecookie-seven.vercel.app/")
    )
    if role == "admin":
        builder.button(text="👑 Адмін-панель", callback_data="main_admin")

    # Розташовуємо по одній кнопці в ряд
    builder.adjust(1)

    return builder.as_markup()


def get_start_menu_kb(role: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="📲 Мій QR-код", callback_data="main_qr")
    builder.button(text="🏠 Головне меню", callback_data="main_menu")

    if role == "admin":
        builder.button(text="👑 Адмін-панель", callback_data="main_admin")

    # Розташовуємо по одній кнопці в ряд
    builder.adjust(1)

    return builder.as_markup()
