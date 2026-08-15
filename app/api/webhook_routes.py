import re
from fastapi import APIRouter, Request, Depends
from aiogram import Bot

from app.repositories.payment_repository import get_payment_by_invoice, update_payment_status
from app.services.coin_service import process_coin_transaction

mono_router = APIRouter()


@mono_router.get("/")
async def root():
    return {"status": "FastAPI is running and ready for Webhooks"}


@mono_router.get("/mono")
async def mono_webhook_get():
    """Обробка тестових GET-запитів від Монобанку"""
    return {"status": "OK"}


@mono_router.post("/mono")
async def mono_webhook(request: Request):
    try:
        data = await request.json()
        print(f"🔥 [МОНОБАНК RAW]: {data}")
        if data.get("type") == "StatementItem":
            item = data["data"]["statementItem"]
            raw_amount = item.get("amount", 0)
            if raw_amount <= 0:
                return {"status": "OK"}
            incoming_amount_uah = raw_amount / 100

            desc = item.get("description", "")
            comm = item.get("comment", "")
            full_text = f"{desc} {comm}".strip()
            match = re.search(r'(pay_[a-f0-9]{8})', full_text)
            if match:
                invoice_id = match.group(1)

                session_factory = request.app.state.session_factory
                bot: Bot = request.app.state.bot
                async with session_factory() as session:
                    payment = await get_payment_by_invoice(session, invoice_id)
                    if payment:
                        if payment.status == "PAID":
                            print(f"♻️ Платіж {invoice_id} вже оброблено.")
                            return {"status": "OK"}
                        payment.amount = int(incoming_amount_uah)
                        await update_payment_status(session, payment, "PAID")

                        await process_coin_transaction(
                            session=session,
                            telegram_id=payment.telegram_id,
                            amount=payment.amount,
                            feature="shop_topup"
                        )
                        await bot.send_message(
                            chat_id=payment.telegram_id,
                            text=(
                                f"🎉 <b>Оплату успішно зараховано!</b>\n\n"
                                f"Вам нараховано <b>+{payment.amount} 🦝</b> Єнот-токенів."
                            ),
                            parse_mode="HTML"
                        )
    except Exception as e:
        print(f"❌ [ПОМИЛКА ВЕБХУКУ]: {e}")

    return {"status": "OK"}
