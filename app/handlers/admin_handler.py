from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.context import FSMContext
from app.filters.admin_filter import AdminFilter
from app.keyboards.admin_keyboard import get_admin_main_kb, get_broadcast_target_kb
from app.repositories.qr_repository import get_users_on_territory_count
from app.repositories.user_repository import update_user_role

from app.states.admin_states import AdminRoleState, BroadcastState
admin_router = Router()

admin_router.message.filter(AdminFilter())
admin_router.callback_query.filter(AdminFilter())


@admin_router.message(Command("admin"))
async def admin_panel_handler(message: Message):
    """Обробник команди /admin"""
    await message.answer(
        "👋 Вітаю в панелі адміністратора!\n\nОберіть потрібну дію з меню нижче:",
        reply_markup=get_admin_main_kb()
    )


@admin_router.callback_query(F.data == "admin_cancel")
async def cancel_action_handler(callback: CallbackQuery):
    """Повертає адміна до головного меню"""
    await callback.message.edit_text(
        "👋 Вітаю в панелі адміністратора!\n\nОберіть потрібну дію з меню нижче:",
        reply_markup=get_admin_main_kb()
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_stats")
async def show_stats_handler(callback: CallbackQuery, session: AsyncSession):
    count = await get_users_on_territory_count(session)

    await callback.message.answer(f"📊 Зараз на території перебуває: {count} осіб.")
    await callback.answer()


@admin_router.callback_query(F.data == "admin_assign_admin")
async def assign_admin_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminRoleState.waiting_for_admin_id)
    await callback.message.answer("✍️ Введіть Telegram ID користувача, якого хочете призначити Адміністратором:")
    await callback.answer()


@admin_router.message(AdminRoleState.waiting_for_admin_id)
async def process_admin_id(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text.isdigit():
        await message.answer("⚠️ Помилка! ID має містити лише цифри. Спробуйте ще раз:")
        return

    user_id = int(message.text)

    updated_user = await update_user_role(session, user_id, "admin")

    if updated_user is None:
        await message.answer("❌ Користувача з таким ID не знайдено в базі даних.")
    else:
        await message.answer(f"✅ Успішно! Користувачу {user_id} надано роль Адміністратора.")

    await state.clear()


@admin_router.callback_query(F.data == "admin_assign_volunteer")
async def assign_volunteer_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminRoleState.waiting_for_volunteer_id)
    await callback.message.answer("✍️ Введіть Telegram ID користувача, якого хочете призначити Волонтером:")
    await callback.answer()


@admin_router.message(AdminRoleState.waiting_for_volunteer_id)
async def process_volunteer_id(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text.isdigit():
        await message.answer("⚠️ Помилка! ID має містити лише цифри. Спробуйте ще раз:")
        return

    user_id = int(message.text)

    updated_user = await update_user_role(session, user_id, "volunteer")

    if updated_user is None:
        await message.answer("❌ Користувача з таким ID не знайдено в базі даних.")
    else:
        await message.answer(f"✅ Успішно! Користувачу {user_id} надано роль Волонтера.")

    await state.clear()


@admin_router.callback_query(F.data == "admin_broadcast")
async def broadcast_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "📢 Оберіть аудиторію для розсилки оголошення:",
        reply_markup=get_broadcast_target_kb()
    )
    await callback.answer()


@admin_router.callback_query(F.data.in_(["broadcast_on", "broadcast_off", "broadcast_all"]))
async def ask_broadcast_message(callback: CallbackQuery, state: FSMContext):
    target = callback.data.split("_")[1]

    await state.update_data(target=target)
    await state.set_state(BroadcastState.waiting_for_message)

    await callback.message.edit_text(
        "✍️ Надішліть текст оголошення (можна форматувати текст):\n\n"
        "<i>Щоб скасувати, натисніть відповідну кнопку в попередньому меню.</i>",
        parse_mode="HTML"
    )
    await callback.answer()
