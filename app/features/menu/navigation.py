from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from app.core.models import User
from app.shared.main_keyboard import get_main_menu_kb, get_freshman_menu_kb

navigation_router = Router(name="navigation")

@navigation_router.message(Command("cancel"))
@navigation_router.message(F.text == "❌ Скасувати")
async def cancel(message: Message, state: FSMContext, session):
    await state.clear()
    await message.answer("Дію скасовано.", reply_markup=ReplyKeyboardRemove())
    user = await session.get(User, message.from_user.id)
    await message.answer("Головне меню", reply_markup=get_main_menu_kb(user.user_role if user else "guest", message.from_user.id))

@navigation_router.callback_query(F.data == "freshman_home")
async def freshman(callback: CallbackQuery, state: FSMContext, session):
    await state.clear()
    await callback.answer()
    user = await session.get(User, callback.from_user.id)
    if not user:
        return await callback.message.answer("Для цього розділу зареєструйтеся через /register.")
    await callback.message.answer("🎉 Тиждень першокурсника", reply_markup=get_freshman_menu_kb(user.user_role))


from aiogram.filters import BaseFilter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

class GuestFilter(BaseFilter):
    async def __call__(self,event,session):
        return not await session.get(User,event.from_user.id)

@navigation_router.callback_query(F.data.in_({"ticket:home","ticket:orders","main_profile"}),GuestFilter())
async def guest_registration(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("Для цього розділу зареєструйтеся.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Зареєструватися",callback_data="main_register")]]))

@navigation_router.message(F.text == "🏠 Головне меню")
async def home_text(message: Message,state: FSMContext,session):
    await state.clear()
    user=await session.get(User,message.from_user.id)
    await message.answer("Головне меню",reply_markup=get_main_menu_kb(user.user_role if user else "guest",message.from_user.id))
