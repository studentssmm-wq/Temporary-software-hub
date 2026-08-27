
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


def get_schedule_days_user_kb(days: list[int]) -> InlineKeyboardMarkup:
    """Клавіатура для вибору дня"""
    builder = InlineKeyboardBuilder()
    for d in days:
        builder.button(text=f"{d} число", callback_data=f"show_day_{d}")

    builder.adjust(3)
    builder.row(InlineKeyboardButton(
        text="🔙 Головне меню", callback_data="main_menu"))
    return builder.as_markup()


def get_schedule_pagination_kb(day: int, current_index: int, total: int) -> InlineKeyboardMarkup:
    """Клавіатура для гортання картинок"""
    builder = InlineKeyboardBuilder()

    # Якщо картинка лише одна, кнопки "Вперед/Назад" не додаємо
    if total > 1:
        # Робимо безкінечну карусель (після останньої -> перша)
        prev_idx = current_index - 1 if current_index > 0 else total - 1
        next_idx = current_index + 1 if current_index < total - 1 else 0

        builder.row(
            InlineKeyboardButton(
                text="⬅️", callback_data=f"sched_page_{day}_{prev_idx}"),
            InlineKeyboardButton(
                text=f"{current_index + 1} / {total}", callback_data="ignore"),
            InlineKeyboardButton(
                text="➡️", callback_data=f"sched_page_{day}_{next_idx}")
        )

    builder.row(InlineKeyboardButton(
        text="🔙 До списку днів", callback_data="event_schedule"))
    return builder.as_markup()
