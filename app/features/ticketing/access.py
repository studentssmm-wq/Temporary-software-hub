import logging
from aiogram import BaseMiddleware
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from app.core.models import User
from app.features.ticketing.logic import BookingError
from app.features.ticketing.runtime import db, BLACKLIST_CACHE
from app.shared.admin_filter import is_admin

logger = logging.getLogger(__name__)

class TicketAccessFilter(BaseFilter):
    async def __call__(self, event, session):
        if not event.from_user:
            return False
        if await session.get(User,event.from_user.id):
            return True
        return bool(isinstance(event,Message) and event.web_app_data and await is_admin(event.from_user.id,session))

class TicketSafetyMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id
        username = event.from_user.username or ""
        admin = await is_admin(user_id, data["session"])
        if not admin and username and username.lower() in BLACKLIST_CACHE:
            await self.respond(event, "Ви заблоковані у модулі квитків. Зверніться до підтримки.")
            return
        state = data.get("state")
        current_state = await state.get_state() if state else None
        if isinstance(event, Message) and event.web_app_data:
            raw = event.web_app_data.data or ""
            if (raw.startswith("admin_seat|") or (current_state or "").startswith("AddEventState:")) and not admin:
                await event.answer("Ця дія доступна лише адміністраторам.")
                return
            if len(raw) > 4096:
                await event.answer("Забагато місць в одному запиті.")
                return
        if isinstance(event, CallbackQuery) and event.data.startswith("ticket:forgot_"):
            try:
                order_id = int(event.data.rsplit("_", 1)[1])
            except ValueError:
                return await event.answer("Некоректне замовлення", show_alert=True)
            order = await db.get_order(order_id)
            if not order or order["user_id"] != user_id or order["status"] not in {"pending","pending_manual"}:
                return await event.answer("Це замовлення недоступне", show_alert=True)
        if current_state == "OrderState:waiting_for_proof" and isinstance(event, Message):
            order_id = (await state.get_data()).get("manual_order_id")
            order = await db.get_order(order_id) if order_id else None
            if not order or order["user_id"] != user_id or order["status"] not in {"pending","pending_manual"}:
                await state.clear()
                return await event.answer("Замовлення недоступне. Відкрийте список подій знову.")
        allowed_media={"AddEventState:photo","AdminTickets:uploading","AdminTickets:mass_uploading","OrderState:waiting_for_proof","AdminBroadcast:waiting_for_message"}
        if isinstance(event,Message) and current_state and not event.text and not event.web_app_data and current_state not in allowed_media:
            return await event.answer("На цьому кроці введіть відповідь текстом або /cancel.")
        try:
            return await handler(event, data)
        except (BookingError, ValueError, KeyError, IndexError) as error:
            logger.warning("Rejected invalid ticket action: %s", type(error).__name__)
            await self.respond(event, str(error) if isinstance(error, BookingError) else "Дані некоректні або дія застаріла. Спробуйте ще раз; /cancel скасовує діалог.")

    async def respond(self, event, text):
        if isinstance(event, CallbackQuery):
            await event.answer(text[:180], show_alert=True)
        else:
            await event.answer(text)
