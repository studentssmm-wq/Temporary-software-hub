from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import find_user_by_id
from app.services.payment_service import generate_payment_link

profile_router = Router()

# Допоміжна функція для клавіатури профілю


def get_profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        # [InlineKeyboardButton(text="🦝 Поповнити баланс",
        #                       callback_data="topup_balance")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])


@profile_router.callback_query(F.data == "main_profile")
async def show_profile_handler(callback: CallbackQuery, session: AsyncSession):
    user = await find_user_by_id(session, callback.from_user.id)
    if not user:
        await callback.message.answer("Будь ласка, зареєструйтесь через /start")
        await callback.answer()
        return

    full_name = f"{user.last_name or ''} {user.first_name}".strip()

    if user.institute and user.student_group:
        status_info = (
            f"🏢 <b>Інститут:</b> {user.institute}\n"
            f"📚 <b>Група:</b> {user.student_group}"
        )
    else:
        status_info = f"💼 <b>Статус:</b> {user.non_student_type or 'Гість'}"

    system_role = "Адміністратор" if user.user_role == "admin" else "Користувач"

    # Додали відображення балансу (user.coins)
    profile_text = (
        f"👤 <b>Ваш профіль</b>\n"
        f"──────────────\n"
        f"📝 <b>Ім'я:</b> {full_name}\n"
        f"{status_info}\n"
        f"🎂 <b>Дата народження:</b> {user.birth_date.strftime('%d.%m.%Y')}\n"
        f"🚻 <b>Стать:</b> {user.gender}\n"
        f"──────────────\n"
        # f"🦝 <b>Баланс:</b> <b>{user.coins}</b> Єнот-токенів\n"
        f"🛡 <b>Роль:</b> {system_role}\n"
    )

    await callback.message.edit_text(
        text=profile_text,
        parse_mode="HTML",
        reply_markup=get_profile_kb()
    )
    await callback.answer()


@profile_router.callback_query(F.data == "topup_balance")
async def topup_balance_handler(callback: CallbackQuery, session: AsyncSession):
    # Генеруємо платіжне посилання через наш сервіс
    unique_comment, payment_link = await generate_payment_link(session, callback.from_user.id)

    # Створюємо клавіатуру з URL-кнопкою
    pay_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💳 Оплатити через Monobank", url=payment_link)],
        [InlineKeyboardButton(text="🔙 Назад до профілю",
                              callback_data="main_profile")]
    ])

    text = (
        "💳 <b>Поповнення балансу</b>\n\n"
        "Натисніть кнопку нижче, щоб безпечно перейти до оплати через Монобанк.\n\n"
        "💡 <i>Ви можете ввести будь-яку суму. 1 грн = 1 🦝 Єнот-токен.</i>\n\n"
        "⚠️ <b>Важливо:</b> Не змінюйте коментар до платежу, інакше система не зможе автоматично нарахувати вам токени!"
    )

    await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=pay_kb)
    await callback.answer()
