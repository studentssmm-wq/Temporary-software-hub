"""Atomic processing for ticket orders and the existing coin balance."""
import re
from decimal import Decimal
from sqlalchemy import text
from app.core.database import session_maker
from app.features.ticketing.logic import payment_reference

async def process_statement(item):
    if item.get("hold") is True:
        return {"status":"ignored", "reason":"hold"}
    tx_id = item.get("id")
    minor = item.get("amount")
    if not isinstance(tx_id,str) or not tx_id or len(tx_id)>255 or not isinstance(minor,int) or isinstance(minor,bool) or minor<=0:
        return {"status":"ignored"}
    if item.get("currencyCode") != 980:
        return {"status":"ignored","reason":"currency"}
    description = f"{item.get('description','')} {item.get('comment','')}"
    order_id = payment_reference(description)
    coin_match = re.search(r"(?<![a-z0-9_])(pay_[a-f0-9]{8})(?![a-z0-9_])", description)
    if not order_id and not coin_match:
        return {"status":"ignored"}
    paid = Decimal(minor)/100
    async with session_maker() as session:
        if order_id:
            row = (await session.execute(text("SELECT * FROM orders WHERE id=:id FOR UPDATE"), {"id":order_id})).mappings().first()
            if not row:
                return {"status":"ignored","reason":"order-unavailable"}
            if row["status"] in {"cancelled","rejected"}:
                recorded=(await session.execute(text("INSERT INTO processed_transactions(tx_id,order_id,amount) VALUES (:tx,:order_id,:amount) ON CONFLICT (tx_id) DO NOTHING RETURNING tx_id"),
                    {"tx":tx_id,"order_id":order_id,"amount":paid})).scalar()
                if not recorded:
                    return {"status":"duplicate"}
                await session.commit()
                return {"status":"requires_review","order_id":order_id,"user_id":row["user_id"],"amount":str(paid)}
        else:
            row = (await session.execute(text("SELECT * FROM payments WHERE invoice_id=:invoice FOR UPDATE"), {"invoice":coin_match.group(1)})).mappings().first()
            if not row or row["status"] == "PAID":
                return {"status":"ignored"}
        inserted = (await session.execute(text("""INSERT INTO processed_transactions(tx_id,order_id,amount)
            VALUES (:tx,:order_id,:amount) ON CONFLICT (tx_id) DO NOTHING RETURNING tx_id"""),
            {"tx":tx_id,"order_id":order_id,"amount":paid})).scalar()
        if not inserted:
            return {"status":"duplicate", "retry_order_id":order_id if order_id and row["status"]=="confirmed" and not row["is_ticket_given"] else None}
        if order_id:
            total = (row["paid_amount"] or Decimal(0)) + paid
            confirmed = total >= row["required_amount"]

            status = "confirmed" if confirmed or row["status"] == "confirmed" else row["status"]
            await session.execute(text("UPDATE orders SET paid_amount=:amount,status=:status WHERE id=:id"), {"amount":total,"status":status,"id":order_id})
            result={"status":"processed","order_id":order_id,"user_id":row["user_id"],"confirmed":status=="confirmed","paid":str(total),"required":str(row["required_amount"])}
        else:
            coins = int(paid)
            await session.execute(text("UPDATE payments SET amount=:amount,status='PAID' WHERE id=:id"), {"amount":coins,"id":row["id"]})
            await session.execute(text("UPDATE users SET coins=coins+:coins WHERE telegram_id=:id"), {"coins":coins,"id":row["telegram_id"]})
            await session.execute(text("INSERT INTO coin_transactions(id,telegram_id,amount,feature) VALUES (gen_random_uuid(),:id,:coins,'shop_topup')"), {"id":row["telegram_id"],"coins":coins})
            result={"status":"processed","user_id":row["telegram_id"],"coins":coins}
        await session.commit()
        return result
