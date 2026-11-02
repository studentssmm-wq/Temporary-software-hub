from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.users.user_repository import find_user_by_id
from app.shared.main_keyboard import get_main_menu_kb

menu_router = Router()


@menu_router.message(Command("menu"))
async def menu_command_handler(message: Message, session: AsyncSession):
    if message.from_user is None:
        return

    user = await find_user_by_id(session, message.from_user.id)

    if user:
        await message.answer(
            "📋 Головне меню:\nОберіть потрібний розділ:",
            reply_markup=get_main_menu_kb(user.user_role),
        )
    else:
        await message.answer(
            "❌ Ви ще не зареєстровані. Натисніть /start для реєстрації."
        )


@menu_router.callback_query(F.data == "main_menu")
async def main_menu_callback_handler(callback: CallbackQuery, session: AsyncSession):
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    user = await find_user_by_id(session, callback.from_user.id)

    if user:
        text = "📋 Головне меню:\nОберіть потрібний розділ:"
        keyboard = get_main_menu_kb(user.user_role)
        if callback.message.text is None:
            await callback.message.answer(text, reply_markup=keyboard)
        elif callback.message.text != text or callback.message.reply_markup != keyboard:
            await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.message.answer(
            "❌ Ви ще не зареєстровані. Натисніть /start для реєстрації."
        )

    await callback.answer()

