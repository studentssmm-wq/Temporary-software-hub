import json
from aiogram.types import BufferedInputFile
from sqlalchemy import text
from app.core.database import session_maker
from app.features.ticketing.ticket_generator import create_personalized_ticket

async def deliver_order(order_id, bot, user_id=None):
    """Only confirmed orders can deliver tickets. Retrying a failed delivery is supported."""
    async with session_maker() as session:
        order = (await session.execute(text("SELECT * FROM orders WHERE id=:id FOR UPDATE"), {"id":order_id})).mappings().first()
        if not order or (user_id is not None and order["user_id"] != user_id) or order["status"] != "confirmed":
            return False
        if order["is_ticket_given"]:
            await bot.send_message(order["user_id"], f"Квитки замовлення NULP-{order_id} вже надіслано вище в чаті.")
            return True
        event = (await session.execute(text("SELECT * FROM events WHERE id=:id"), {"id":order["event_id"]})).mappings().one()
        keys = (await session.execute(text("SELECT seat_key FROM order_seats WHERE order_id=:id ORDER BY seat_key"), {"id":order_id})).scalars().all()
        all_delivered = True
        if keys:
            for key in keys:
                parts = key.rsplit("-", 1)
                row = parts[0]
                seat = parts[1]
                ticket = (await session.execute(text("SELECT * FROM seat_tickets WHERE event_id=:event AND row_num=:row AND seat_num=:seat"),
                    {"event":event["id"],"row":row,"seat":seat})).mappings().first()
                if ticket:
                    method = bot.send_photo if ticket["file_type"] == "photo" else bot.send_document
                    await method(order["user_id"], ticket["file_id"], caption=f"NULP-{order_id} | {key}")
                elif event["generates_qr_ticket"]:
                    image = create_personalized_ticket(order_id, event["title"], key)
                    await bot.send_photo(order["user_id"], BufferedInputFile(image.getvalue(),filename=f"ticket-{order_id}.png"))
                else:
                    all_delivered = False
                    await bot.send_message(order["user_id"], f"Бронювання {key} збережено. Файл квитка організатори ще не завантажили. Повторіть видачу з «Мої замовлення» пізніше.")
        elif event["generates_qr_ticket"]:
            image = create_personalized_ticket(order_id, event["title"])
            await bot.send_photo(order["user_id"], BufferedInputFile(image.getvalue(), filename=f"ticket-{order_id}.png"), caption=f"Кількість квитків: {order['ticket_count']}")
        else:
            await bot.send_message(order["user_id"], f"Замовлення NULP-{order_id} підтверджено. Квитків: {order['ticket_count']}.\n{event['success_message'] or ''}")
        if all_delivered:
            await session.execute(text("UPDATE orders SET is_ticket_given=TRUE WHERE id=:id"), {"id":order_id})
        await session.commit()
        return all_delivered
