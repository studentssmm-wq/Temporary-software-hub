import hmac
import logging
import os
from aiogram.exceptions import TelegramAPIError
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from app.core.config import ENABLE_PAYMENTS, mono_webhook_secret
from app.features.payments.monobank_service import process_statement
from app.features.ticketing.delivery import deliver_order

logger=logging.getLogger(__name__)
mono_router=APIRouter()

@mono_router.get("/mono/{secret}")
async def mono_probe(secret: str):
    authorize(secret)
    return {"status":"OK"}


def authorize(secret):
    expected=mono_webhook_secret()
    if not ENABLE_PAYMENTS or len(expected)<32:
        raise HTTPException(status_code=503,detail="Payment integration disabled")
    if not hmac.compare_digest(secret,expected):
        raise HTTPException(status_code=403,detail="Forbidden")


@mono_router.post("/mono/{secret}")
async def mono_webhook(secret: str, request: Request, background_tasks: BackgroundTasks):
    authorize(secret)
    try:
        data=await request.json()
    except ValueError:
        raise HTTPException(status_code=400,detail="Invalid JSON") from None
    if not isinstance(data,dict) or data.get("type")!="StatementItem":
        return {"status":"OK"}
    statement=data.get("data")
    if not isinstance(statement,dict):
        raise HTTPException(status_code=400,detail="Invalid statement envelope")
    item=statement.get("statementItem",{})
    if not isinstance(item,dict):
        raise HTTPException(status_code=400,detail="Invalid statement")
    result=await process_statement(item)
    background_tasks.add_task(payment_effects, result, request.app.state.bot)
    return {"status":"OK"}


async def payment_effects(result, bot):
    try:
        await notify_payment(result, bot)
    except Exception as error:
        logger.warning('Payment saved; follow-up failed: %s', type(error).__name__)


async def notify_payment(result, bot):
    if result.get('retry_order_id'):
        await deliver_order(result['retry_order_id'], bot)
    if result["status"]=="requires_review":
        from app.features.ticketing.runtime import get_admin_ids
        recipients=await get_admin_ids()
        messages=[(result["user_id"],f"Отримано {result['amount']} грн за скасоване або відхилене замовлення NULP-{result['order_id']}. Квиток автоматично не видається. Зверніться до підтримки для перевірки оплати.")]
        messages.extend((admin_id,f"Потрібна ручна перевірка: {result['amount']} грн за скасоване/відхилене NULP-{result['order_id']}. Транзакцію збережено, квиток не видано.") for admin_id in recipients)
        for chat_id,message in messages:
            try:
                await bot.send_message(chat_id,message)
            except TelegramAPIError:
                logger.warning("Review payment recorded; recipient notification unavailable")
    if result["status"]=="processed":
        if result.get("order_id"):
            from app.features.ticketing.runtime import db
            from app.features.ticketing import sheets
            order=await db.get_order(result["order_id"])
            event=await db.get_event(order["event_id"])
            try:
                await sheets.update_payment_in_sheet(event["title"],order["id"],"Підтверджено" if result.get("confirmed") else f"Недоплата (є {result['paid']} з {result['required']})",event["venue_type"])
            except Exception as error:
                logger.warning('Payment saved; Sheets update failed: %s', type(error).__name__)
        try:
            if result.get("order_id") and result.get("confirmed"):
                await bot.send_message(result['user_id'],f"Оплату NULP-{result['order_id']} отримано: {result['paid']} грн.\n{event['success_message'] or ''}")
                await deliver_order(result["order_id"],bot)
                from app.features.ticketing.runtime import get_admin_ids
                for admin_id in await get_admin_ids():
                    try:
                        await bot.send_message(admin_id,f"Авто-підтвердження Monobank: NULP-{result['order_id']}. Сплачено {result['paid']} грн. Квитків: {order['ticket_count']}.")
                    except TelegramAPIError:
                        logger.warning('Payment saved; admin notification unavailable')
            elif result.get("order_id"):
                await bot.send_message(result["user_id"],f"NULP-{result['order_id']}: сплачено {result['paid']} з {result['required']} грн.")
            else:
                await bot.send_message(result["user_id"],f"Зараховано {result['coins']} Єнот-токенів.")
        except TelegramAPIError:

            logger.warning("Payment committed; Telegram notification could not be delivered")
