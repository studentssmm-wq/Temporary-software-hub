from contextlib import suppress
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.song_repository import (
    get_all_songs, get_song_by_id, create_song, update_song, delete_song
)
from app.keyboards.song_keyboard import (
    get_songs_list_kb, get_song_view_kb, get_cancel_song_kb, get_empty_songs_kb
)
from app.states.song_states import SongCreateState, SongEditState

song_router = Router()

# ============================
# ДЛЯ КОРИСТУВАЧІВ (СТУДЕНТІВ)
# ============================


@song_router.callback_query(F.data == "user_songs_menu")
async def user_songs_menu_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await state.clear()
    songs = await get_all_songs(session)

    with suppress(TelegramBadRequest):
        if not songs:
            await callback.message.edit_text(
                "📖 <b>Пісенник порожній.</b>\nПісні ще не були додані організаторами.",
                parse_mode="HTML",
                reply_markup=get_empty_songs_kb(is_admin=False)
            )
        else:
            await callback.message.edit_text(
                "📖 <b>Студентський Пісенник</b>\n\nОберіть пісню зі списку для перегляду слів:",
                parse_mode="HTML",
                reply_markup=get_songs_list_kb(songs, is_admin=False, page=0)
            )
    await callback.answer()


@song_router.callback_query(F.data.startswith("songs_page_user_"))
async def user_songs_pagination_handler(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split("_")[-1])
    songs = await get_all_songs(session)
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(
            reply_markup=get_songs_list_kb(songs, is_admin=False, page=page)
        )
    await callback.answer()


@song_router.callback_query(F.data.startswith("user_song_view_"))
async def user_song_view_handler(callback: CallbackQuery, session: AsyncSession):
    song_id = int(callback.data.split("_")[-1])
    song = await get_song_by_id(session, song_id)
    if not song:
        await callback.answer("Пісню не знайдено.", show_alert=True)
        return

    text = f"🎵 <b>{song.title}</b>\n\n{song.lyrics}"
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=get_song_view_kb(is_admin=False)
        )
    await callback.answer()


# ============================
# АДМІНКА (CRUD)
# ============================

@song_router.callback_query(F.data == "admin_songs_menu")
async def admin_songs_menu_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await state.clear()
    songs = await get_all_songs(session)

    with suppress(TelegramBadRequest):
        if not songs:
            await callback.message.edit_text(
                "📖 <b>Пісенник порожній.</b>\nДодайте першу пісню за допомогою кнопки нижче:",
                parse_mode="HTML",
                reply_markup=get_empty_songs_kb(is_admin=True)
            )
        else:
            await callback.message.edit_text(
                "📖 <b>Керування пісенником</b>\n\nОберіть пісню для редагування/видалення або додайте нову:",
                parse_mode="HTML",
                reply_markup=get_songs_list_kb(songs, is_admin=True, page=0)
            )
    await callback.answer()


@song_router.callback_query(F.data.startswith("songs_page_admin_"))
async def admin_songs_pagination_handler(callback: CallbackQuery, session: AsyncSession):
    page = int(callback.data.split("_")[-1])
    songs = await get_all_songs(session)
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(
            reply_markup=get_songs_list_kb(songs, is_admin=True, page=page)
        )
    await callback.answer()


@song_router.callback_query(F.data.startswith("admin_song_view_"))
async def admin_song_view_handler(callback: CallbackQuery, session: AsyncSession):
    song_id = int(callback.data.split("_")[-1])
    song = await get_song_by_id(session, song_id)
    if not song:
        await callback.answer("Пісню не знайдено.", show_alert=True)
        return

    text = f"🎵 <b>{song.title}</b>\n\n{song.lyrics}"
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=get_song_view_kb(is_admin=True, song_id=song.id)
        )
    await callback.answer()


# --- СТВОРЕННЯ ПІСНІ ---

@song_router.callback_query(F.data == "admin_song_add")
async def admin_song_add_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SongCreateState.waiting_for_title)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            "✍️ Введіть <b>назву</b> нової пісні:",
            parse_mode="HTML",
            reply_markup=get_cancel_song_kb(is_admin=True)
        )
    await callback.answer()


@song_router.message(SongCreateState.waiting_for_title)
async def admin_song_add_title(message: Message, state: FSMContext):
    title = message.text.strip()
    await state.update_data(title=title)
    await state.set_state(SongCreateState.waiting_for_lyrics)
    await message.answer(
        f"Назва: <b>{title}</b>\n\nТепер надішліть <b>текст пісні</b> (слова, акорди тощо):",
        parse_mode="HTML",
        reply_markup=get_cancel_song_kb(is_admin=True)
    )


@song_router.message(SongCreateState.waiting_for_lyrics)
async def admin_song_add_lyrics(message: Message, state: FSMContext, session: AsyncSession):
    lyrics = message.text or message.html_text
    data = await state.get_data()
    title = data["title"]

    await create_song(session, title=title, lyrics=lyrics)
    await state.clear()
    await message.answer(
        f"✅ Пісню <b>{title}</b> успішно додано до пісенника!",
        parse_mode="HTML"
    )
    songs = await get_all_songs(session)
    await message.answer(
        "📖 <b>Керування пісенником</b>:",
        parse_mode="HTML",
        reply_markup=get_songs_list_kb(songs, is_admin=True, page=0)
    )


# --- РЕДАГУВАННЯ ПІСНІ ---

@song_router.callback_query(F.data.startswith("song_edit_title_"))
async def admin_song_edit_title_start(callback: CallbackQuery, state: FSMContext):
    song_id = int(callback.data.split("_")[-1])
    await state.update_data(song_id=song_id)
    await state.set_state(SongEditState.waiting_for_new_title)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            "✍️ Введіть <b>нову назву</b> для цієї пісні:",
            parse_mode="HTML",
            reply_markup=get_cancel_song_kb(is_admin=True)
        )
    await callback.answer()


@song_router.message(SongEditState.waiting_for_new_title)
async def admin_song_edit_title_process(message: Message, state: FSMContext, session: AsyncSession):
    new_title = message.text.strip()
    data = await state.get_data()
    song_id = data["song_id"]

    await update_song(session, song_id=song_id, title=new_title)
    await state.clear()
    await message.answer(f"✅ Назву змінено на: <b>{new_title}</b>", parse_mode="HTML")

    songs = await get_all_songs(session)
    await message.answer(
        "📖 <b>Керування пісенником</b>:",
        parse_mode="HTML",
        reply_markup=get_songs_list_kb(songs, is_admin=True, page=0)
    )


@song_router.callback_query(F.data.startswith("song_edit_lyrics_"))
async def admin_song_edit_lyrics_start(callback: CallbackQuery, state: FSMContext):
    song_id = int(callback.data.split("_")[-1])
    await state.update_data(song_id=song_id)
    await state.set_state(SongEditState.waiting_for_new_lyrics)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            "📝 Надішліть <b>новий текст</b> пісні:",
            parse_mode="HTML",
            reply_markup=get_cancel_song_kb(is_admin=True)
        )
    await callback.answer()


@song_router.message(SongEditState.waiting_for_new_lyrics)
async def admin_song_edit_lyrics_process(message: Message, state: FSMContext, session: AsyncSession):
    new_lyrics = message.text or message.html_text
    data = await state.get_data()
    song_id = data["song_id"]

    await update_song(session, song_id=song_id, lyrics=new_lyrics)
    await state.clear()
    await message.answer("✅ Текст пісні успішно оновлено!", parse_mode="HTML")

    songs = await get_all_songs(session)
    await message.answer(
        "📖 <b>Керування пісенником</b>:",
        parse_mode="HTML",
        reply_markup=get_songs_list_kb(songs, is_admin=True, page=0)
    )


# --- ВИДАЛЕННЯ ПІСНІ ---

@song_router.callback_query(F.data.startswith("song_delete_"))
async def admin_song_delete(callback: CallbackQuery, session: AsyncSession):
    song_id = int(callback.data.split("_")[-1])
    success = await delete_song(session, song_id)
    if success:
        await callback.answer("🗑 Пісню видалено!", show_alert=True)
    else:
        await callback.answer("Помилка при видаленні.", show_alert=True)

    songs = await get_all_songs(session)
    with suppress(TelegramBadRequest):
        if not songs:
            await callback.message.edit_text(
                "📖 <b>Пісенник порожній.</b>\nДодайте першу пісню за допомогою кнопки нижче:",
                parse_mode="HTML",
                reply_markup=get_empty_songs_kb(is_admin=True)
            )
        else:
            await callback.message.edit_text(
                "📖 <b>Керування пісенником</b>:",
                parse_mode="HTML",
                reply_markup=get_songs_list_kb(songs, is_admin=True, page=0)
            )
