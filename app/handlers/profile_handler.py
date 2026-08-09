from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import find_user_by_id

profile_router = Router()


@profile_router.callback_query(F.data == "main_profile")
async def show_profile_handler(callback: CallbackQuery, session: AsyncSession):
    user = await find_user_by_id(session, callback.from_user.id)

    if not user:
        await callback.message.answer("❌ Помилка: Ваш профіль не знайдено. Спробуйте /start для реєстрації.")
        await callback.answer()
        return

    full_name = f"{user.last_name or ''} {user.first_name}".strip()

    if user.institute and user.student_group:
        status_info = (
            f"🎓 <b>Інститут:</b> {user.institute}\n"
            f"📚 <b>Група:</b> {user.student_group}"
        )
    else:
        status_info = f"👥 <b>Статус:</b> {user.non_student_type or 'Не вказано'}"

    system_role = "👑 Адміністратор" if user.user_role == "admin" else "👤 Користувач"

    profile_text = (
        f"📋 <b>КАРТКА ПРОФІЛЮ</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🗣 <b>ПІБ:</b> {full_name}\n"
        f"{status_info}\n"
        f"🎂 <b>Дата народження:</b> {user.birth_date.strftime('%d.%m.%Y')}\n"
        f"⚧ <b>Стать:</b> {user.gender}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚙️ <b>Рівень доступу:</b> {system_role}\n"
    )

    await callback.message.answer(text=profile_text, parse_mode="HTML")

    await callback.answer()
