"""FAQ and student support. Existing users and their roles are never rewritten."""
import logging
from html import escape
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import ADMIN_IDS
from app.core.models import User
from app.features.support.models import FAQ, SupportReply, SupportTicket
from app.shared.admin_filter import AdminFilter

logger = logging.getLogger(__name__)
support_router = Router(name="support")
support_admin_router = Router(name="support-admin")
support_admin_router.message.filter(AdminFilter())
support_admin_router.callback_query.filter(AdminFilter())

class SupportState(StatesGroup):
    question = State()
    reply = State()
    category = State()
    faq_question = State()
    answer = State()


def keyboard(items):
    builder = InlineKeyboardBuilder()
    for title, data in items:
        builder.button(text=title[:64], callback_data=data)
    builder.adjust(1)
    return builder.as_markup()


def home_keyboard():
    return keyboard([("❓ Часті питання", "support:faq"), ("✉️ Написати адміністратору", "support:contact"), ("🏠 Головне меню", "main_menu")])


async def send_content(bot, chat_id, text, photo=None, document=None, markup=None):

    caption = text if len(text) <= 1000 else None
    if document:
        await bot.send_document(chat_id, document, caption=caption, reply_markup=markup if caption else None)
    elif photo:
        await bot.send_photo(chat_id, photo, caption=caption, reply_markup=markup if caption else None)
    if not (photo or document) or caption is None:
        for start in range(0, max(len(text), 1), 4000):
            await bot.send_message(chat_id, text[start:start+4000], reply_markup=markup if start+4000 >= len(text) else None)


@support_router.message(Command("faq", "support"))
async def support_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❓ Питання та підтримка", reply_markup=home_keyboard())


@support_router.callback_query(F.data == "support:home")
async def support_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.answer("❓ Питання та підтримка", reply_markup=home_keyboard())


@support_router.callback_query(F.data == "support:faq")
async def categories(callback: CallbackQuery, session: AsyncSession):
    rows = (await session.execute(select(FAQ).order_by(FAQ.category, FAQ.id))).scalars().all()
    seen = set()
    buttons = []
    for row in rows:
        if row.category not in seen:
            buttons.append((row.category, f"support:category:{row.id}"))
            seen.add(row.category)
    buttons.append(("🔙 Назад", "support:home"))
    await callback.answer()
    await callback.message.answer("Оберіть категорію:" if rows else "Базу відповідей ще наповнюють.", reply_markup=keyboard(buttons))


@support_router.callback_query(F.data.startswith("support:category:"))
async def questions(callback: CallbackQuery, session: AsyncSession):
    anchor = await session.get(FAQ, int(callback.data.rsplit(":", 1)[1]))
    await callback.answer()
    if not anchor:
        return await callback.message.answer("Категорія більше не доступна.")
    rows = (await session.execute(select(FAQ).where(FAQ.category == anchor.category).order_by(FAQ.id))).scalars().all()

    for start in range(0, len(rows), 50):
        await callback.message.answer(anchor.category, reply_markup=keyboard([(row.question, f"support:answer:{row.id}") for row in rows[start:start+50]] + [("🔙 Категорії", "support:faq")]))


@support_router.callback_query(F.data.startswith("support:answer:"))
async def answer(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    row = await session.get(FAQ, int(callback.data.rsplit(":", 1)[1]))
    await callback.answer()
    if row:
        await send_content(bot, callback.from_user.id, f"{row.question}\n\n{row.answer}", markup=keyboard([("🔙 До питань", f"support:category:{row.id}")]))
    else:
        await callback.message.answer("Відповідь більше не доступна.")


@support_router.callback_query(F.data == "support:contact")
async def contact(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    if not await session.get(User, callback.from_user.id):
        return await callback.message.answer("Спочатку зареєструйтеся через /register.", reply_markup=keyboard([("Зареєструватися", "main_register")]))
    await state.set_state(SupportState.question)
    await callback.message.answer("Напишіть питання. Можна додати фото або документ. Скасування: /cancel")


@support_router.message(SupportState.question, F.text | F.photo | F.document)
async def submit_question(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    ticket = SupportTicket(user_id=message.from_user.id, username=message.from_user.username,
        text=message.text or message.caption or "Без тексту", photo_id=message.photo[-1].file_id if message.photo else None,
        document_id=message.document.file_id if message.document else None)
    session.add(ticket)
    await session.commit()
    await state.clear()
    admin_ids = set(ADMIN_IDS) | set((await session.execute(select(User.telegram_id).where(User.user_role == "admin"))).scalars())
    delivered = 0
    for admin_id in admin_ids:
        try:
            await send_content(bot, admin_id, f"Звернення #{ticket.id} від {message.from_user.full_name} (ID {ticket.user_id})\n\n{ticket.text}", ticket.photo_id, ticket.document_id, keyboard([("Відповісти", f"support:reply:{ticket.id}")]))
            delivered += 1
        except TelegramAPIError:
            logger.warning("Could not notify a support administrator")
    await message.answer(f"Звернення #{ticket.id} збережено. " + ("Адміністратора повідомлено." if delivered else "Воно доступне адміністраторам у панелі підтримки."))


@support_admin_router.callback_query(F.data == "support:admin")
async def admin_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.answer("Підтримка: керування", reply_markup=keyboard([("📨 Відкриті звернення", "support:pending"), ("➕ Додати відповідь FAQ", "support:add"), ("✏️ Редагувати FAQ", "support:manage"), ("🔙 Адмін-панель", "main_admin")]))


@support_admin_router.callback_query(F.data == "support:pending")
async def pending(callback: CallbackQuery, session: AsyncSession):
    rows = (await session.execute(select(SupportTicket).where(SupportTicket.status == "open").order_by(SupportTicket.id).limit(40))).scalars().all()
    await callback.answer()
    await callback.message.answer("Найстаріші відкриті звернення:" if rows else "Відкритих звернень немає.", reply_markup=keyboard([(f"#{row.id}: {row.text[:40]}", f"support:reply:{row.id}") for row in rows]+[("🔙 Назад", "support:admin")]))


@support_admin_router.callback_query(F.data.startswith("support:reply:"))
async def choose_reply(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot: Bot):
    ticket = await session.get(SupportTicket, int(callback.data.rsplit(":", 1)[1]))
    await callback.answer()
    if not ticket or ticket.status != "open":
        return await callback.message.answer("Звернення вже закрите або не існує.")
    await state.update_data(support_ticket_id=ticket.id)
    await state.set_state(SupportState.reply)
    await send_content(bot, callback.from_user.id, f"Звернення #{ticket.id}\n\n{ticket.text}\n\nНадішліть відповідь або /cancel.", ticket.photo_id, ticket.document_id)


@support_admin_router.message(SupportState.reply, F.text | F.photo | F.document)
async def submit_reply(message: Message, state: FSMContext, session: AsyncSession, bot: Bot):
    data = await state.get_data()

    ticket = (await session.execute(select(SupportTicket).where(SupportTicket.id == data.get("support_ticket_id")).with_for_update())).scalar_one_or_none()
    if not ticket or ticket.status != "open":
        await state.clear()
        return await message.answer("Це звернення вже закрите.")
    text = message.text or message.caption or "Відповідь у вкладенні"
    photo = message.photo[-1].file_id if message.photo else None
    document = message.document.file_id if message.document else None
    try:
        await send_content(bot, ticket.user_id, f"Відповідь на звернення #{ticket.id}\n\n{text}", photo, document)
    except TelegramAPIError:
        await session.rollback()
        return await message.answer("Не вдалося доставити відповідь. Звернення залишилося відкритим.")
    session.add(SupportReply(ticket_id=ticket.id, admin_id=message.from_user.id, text=text, photo_id=photo, document_id=document))
    ticket.status = "closed"
    await session.commit()
    await state.clear()
    await message.answer("Відповідь доставлено, історію збережено.")


@support_admin_router.callback_query(F.data.in_({"support:add", "support:manage"}))
async def faq_manage(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    if callback.data == "support:add":
        await state.clear()
        await state.set_state(SupportState.category)
        return await callback.message.answer("Введіть категорію FAQ:")
    rows = (await session.execute(select(FAQ).order_by(FAQ.id))).scalars().all()
    for start in range(0, max(len(rows), 1), 40):
        await callback.message.answer("Оберіть запис:", reply_markup=keyboard([(f"#{r.id} {r.question[:45]}", f"support:edit:{r.id}") for r in rows[start:start+40]]+[("🔙 Назад", "support:admin")]))


@support_admin_router.callback_query(F.data.startswith("support:edit:"))
async def faq_edit(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    row = await session.get(FAQ, int(callback.data.rsplit(":", 1)[1]))
    await callback.answer()
    if not row:
        return await callback.message.answer("Запис не знайдено.")
    await state.update_data(faq_id=row.id, category=row.category)
    await state.set_state(SupportState.faq_question)
    await callback.message.answer(f"Поточне питання: {row.question}\nВведіть нове питання або /cancel.", reply_markup=keyboard([("🗑 Видалити цей запис", f"support:delete:{row.id}")]))


@support_admin_router.callback_query(F.data.startswith("support:delete:"))
async def faq_delete(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    row = await session.get(FAQ, int(callback.data.rsplit(":", 1)[1]))
    if row:
        await session.delete(row)
        await session.commit()
    await state.clear()
    await callback.answer("Запис видалено")


@support_admin_router.message(SupportState.category, F.text)
async def faq_category(message: Message, state: FSMContext):
    if not message.text.strip():
        return await message.answer("Категорія не може бути порожньою.")
    await state.update_data(category=message.text.strip())
    await state.set_state(SupportState.faq_question)
    await message.answer("Введіть питання:")


@support_admin_router.message(SupportState.faq_question, F.text)
async def faq_question(message: Message, state: FSMContext):
    if not message.text.strip():
        return await message.answer("Питання не може бути порожнім.")
    await state.update_data(question=message.text.strip())
    await state.set_state(SupportState.answer)
    await message.answer("Введіть відповідь:")


@support_admin_router.message(SupportState.answer, F.text)
async def faq_answer(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    row = await session.get(FAQ, data["faq_id"]) if data.get("faq_id") else None
    if data.get("faq_id") and not row:
        await state.clear()
        return await message.answer("Запис уже видалено іншим адміністратором.")
    if row is None:
        row = FAQ(category=data["category"], question=data["question"], answer=message.text)
        session.add(row)
    else:
        row.question, row.answer = data["question"], message.text
    await session.commit()
    await state.clear()
    await message.answer("FAQ збережено.")
