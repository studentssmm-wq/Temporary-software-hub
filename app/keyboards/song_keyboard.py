from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.database.models import Song


def get_songs_list_kb(songs: list[Song], is_admin: bool = False, page: int = 0, per_page: int = 6) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_page_songs = songs[start_idx:end_idx]

    prefix = "admin_song_view_" if is_admin else "user_song_view_"

    for song in current_page_songs:
        builder.row(
            InlineKeyboardButton(
                text=f"🎵 {song.title}",
                callback_data=f"{prefix}{song.id}"
            )
        )

    # Пагінація
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"songs_page_{'admin' if is_admin else 'user'}_{page - 1}")
        )
    if end_idx < len(songs):
        nav_buttons.append(
            InlineKeyboardButton(
                text="Вперед ➡️", callback_data=f"songs_page_{'admin' if is_admin else 'user'}_{page + 1}")
        )
    if nav_buttons:
        builder.row(*nav_buttons)

    if is_admin:
        builder.row(InlineKeyboardButton(
            text="➕ Додати пісню", callback_data="admin_song_add"))
        builder.row(InlineKeyboardButton(
            text="🔙 В адмін-панель", callback_data="main_admin"))
    else:
        builder.row(InlineKeyboardButton(
            text="🔙 Головне меню", callback_data="main_menu"))

    return builder.as_markup()


def get_song_view_kb(is_admin: bool = False, song_id: int | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_admin and song_id is not None:
        builder.row(
            InlineKeyboardButton(
                text="✏️ Назву", callback_data=f"song_edit_title_{song_id}"),
            InlineKeyboardButton(
                text="📝 Текст", callback_data=f"song_edit_lyrics_{song_id}")
        )
        builder.row(
            InlineKeyboardButton(text="🗑 Видалити пісню",
                                 callback_data=f"song_delete_{song_id}")
        )
        builder.row(
            InlineKeyboardButton(text="🔙 До списку пісень",
                                 callback_data="admin_songs_menu")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="🔙 До списку пісень",
                                 callback_data="user_songs_menu")
        )
    return builder.as_markup()


def get_cancel_song_kb(is_admin: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    callback_data = "admin_songs_menu" if is_admin else "user_songs_menu"
    builder.row(InlineKeyboardButton(
        text="❌ Скасувати", callback_data=callback_data))
    return builder.as_markup()


def get_empty_songs_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_admin:
        builder.row(InlineKeyboardButton(
            text="➕ Додати пісню", callback_data="admin_song_add"))
        builder.row(InlineKeyboardButton(
            text="🔙 В адмін-панель", callback_data="main_admin"))
    else:
        builder.row(InlineKeyboardButton(
            text="🔙 Головне меню", callback_data="main_menu"))
    return builder.as_markup()
