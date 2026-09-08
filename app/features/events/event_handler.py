from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InputMediaPhoto, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.events.event_keyboard import (
    get_schedule_days_user_kb,
    get_schedule_pagination_kb,
)
from app.features.events.media_repository import get_media
from app.features.events.schedule_repository import (
    get_schedule_days,
    get_schedule_photos_by_day,
)

event_router = Router()


@event_router.callback_query(F.data == "event_map")
async def event_map_handler(callback: CallbackQuery, session: AsyncSession):
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    file_id = await get_media(session, "map")

    if not file_id:
        await callback.answer(
            "❌ Мапу ще не завантажено адміністратором.", show_alert=True
        )
        return

    await callback.message.answer_photo(
        photo=file_id, caption="🗺 Ось мапа наших подій!"
    )
    await callback.answer()


@event_router.callback_query(F.data == "event_schedule")
async def event_schedule_handler(callback: CallbackQuery, session: AsyncSession):
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    all_days = await get_schedule_days(session)
    days = [day for day in all_days if day != 0]

    if not days:
        await callback.answer("❌ Розкладів ще немає.", show_alert=True)
        return

    await callback.message.delete()
    await callback.message.answer(
        "📅 Оберіть день, розклад якого хочете переглянути:",
        reply_markup=get_schedule_days_user_kb(days),
    )
    await callback.answer()


@event_router.callback_query(F.data == "admin_meeting_view")
async def admin_meeting_view_handler(callback: CallbackQuery, session: AsyncSession):
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    photos = await get_schedule_photos_by_day(session, 0)

    if not photos:
        await callback.answer(
            "❌ Фотографій зустрічі ще не завантажено.", show_alert=True
        )
        return

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photos[0],
        caption="🤝 Зустріч із адміністрацією",
        parse_mode="HTML",
        reply_markup=get_schedule_pagination_kb(0, 0, len(photos)),
    )
    await callback.answer()


@event_router.callback_query(F.data.startswith("show_day_"))
async def show_schedule_day_handler(callback: CallbackQuery, session: AsyncSession):
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    if not callback.data:
        await callback.answer("❌ Недійсний формат розкладу.", show_alert=True)
        return

    try:
        day = int(callback.data.removeprefix("show_day_"))
    except ValueError:
        await callback.answer("❌ Недійсний формат розкладу.", show_alert=True)
        return

    if not 0 <= day <= 31:
        await callback.answer("❌ Недійсний формат розкладу.", show_alert=True)
        return

    photos = await get_schedule_photos_by_day(session, day)

    if not photos:
        await callback.answer("❌ Фотографій не знайдено.", show_alert=True)
        return

    caption_text = (
        "🤝 Зустріч із адміністрацією" if day == 0 else f"📅 Розклад на {day} число"
    )

    await callback.message.delete()
    await callback.message.answer_photo(
        photo=photos[0],
        caption=caption_text,
        parse_mode="HTML",
        reply_markup=get_schedule_pagination_kb(day, 0, len(photos)),
    )
    await callback.answer()


@event_router.callback_query(F.data.startswith("sched_page_"))
async def schedule_pagination_handler(callback: CallbackQuery, session: AsyncSession):
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    if not callback.data:
        await callback.answer("❌ Недійсний формат розкладу.", show_alert=True)
        return

    try:
        _, _, day_str, index_str = callback.data.split("_")
        day, index = int(day_str), int(index_str)
    except ValueError:
        await callback.answer("❌ Недійсний формат розкладу.", show_alert=True)
        return

    if not 0 <= day <= 31:
        await callback.answer("❌ Недійсний формат розкладу.", show_alert=True)
        return

    photos = await get_schedule_photos_by_day(session, day)
    if not 0 <= index < len(photos):
        await callback.answer("❌ Фотографій не знайдено.", show_alert=True)
        return

    caption_text = (
        "🤝 Зустріч із адміністрацією" if day == 0 else f"📅 Розклад на {day} число"
    )
    media = InputMediaPhoto(
        media=photos[index], caption=caption_text, parse_mode="HTML"
    )

    try:
        await callback.message.edit_media(
            media=media,
            reply_markup=get_schedule_pagination_kb(day, index, len(photos)),
        )
    except TelegramBadRequest as error:
        if "message is not modified" not in error.message:
            raise
    await callback.answer()


@event_router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer()


@event_router.callback_query(F.data == "event_rules")
async def event_rules_handler(callback: CallbackQuery):
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    rules_text = (
        "📜 <b>Нагадування про кілька простих правил поведінки під час нашого заходу:</b>\n\n"
        "🚫 Перебувати в стані алкогольного або наркотичного спʼяніння та приносити/вживати алкогольні напої — <b>заборонено</b>.\n"
        "🚬 Паління (у будь-яких його проявах та з використанням будь-яких (не) електронних засобів) на території заходу — <b>заборонено</b>.\n"
        "🔪 Приносити, використовувати будь-які небезпечні предмети — <b>заборонено</b>.\n"
        "🎒 Під час відвідин заходу не залишайте свої особисті речі без нагляду та не залишайте після себе сміття 🗑.\n\n"
        "🤝 Наш захід, зокрема Тиждень першокурсника, це від студентів і для студентів. Це тижні підготовки. Тому не забуваймо ці не надскладні правила поведінки та взаємодії одне з одним до, під час та після заходу.\n\n"
        "⚠️ <i>У випадку порушення правил або неадекватної реакції на зауваження, організатори залишають за собою право попросити покинути подію.</i>"
    )

    await callback.message.answer(rules_text, parse_mode="HTML")
    await callback.answer()


@event_router.callback_query(F.data == "event_shelter")
async def event_shelter_handler(callback: CallbackQuery, session: AsyncSession):
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    video_file_id = await get_media(session, "shelter_video")

    if not video_file_id:
        await callback.answer(
            "❌ Відео з маршрутом до укриття ще не додано адміністратором.",
            show_alert=True,
        )
        return

    await callback.message.answer_video(
        video=video_file_id,
        caption="❤️‍🩹 <b>Маршрут до укриття</b>\n\nБудь ласка, зберігайте спокій та слідуйте інструкціям на відео.",
        parse_mode="HTML",
    )
    await callback.answer()


@event_router.callback_query(F.data == "event_stretching")
async def event_stretching_handler(callback: CallbackQuery, session: AsyncSession):
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    video_file_id = await get_media(session, "stretching_video")

    if not video_file_id:
        await callback.answer(
            "❌ Відео з маршрутом до локації стретчингу ще не додано адміністратором.",
            show_alert=True,
        )
        return

    await callback.message.answer_video(
        video=video_file_id,
        caption="🧘‍♀️ <b>Локація стретчингу</b>\n\nОсь відео-маршрут, як дістатися до нашої локації для розтяжки.",
        parse_mode="HTML",
    )
    await callback.answer()
