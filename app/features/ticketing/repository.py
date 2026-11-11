import asyncio
import json
import re
from decimal import Decimal
from sqlalchemy import text
from app.core.database import session_maker
from app.features.ticketing import sheets
from app.features.ticketing.logic import BookingError, required_total, seat_keys

class SQLAdapter:
    """Bridge existing parameterized queries to the application's shared engine."""
    async def _run(self, query, values, result):
        query = re.sub(r'\$(\d+)', lambda match: ':p' + match.group(1), query)
        async with session_maker() as session:
            rows = await session.execute(text(query), {'p'+str(i): value for i,value in enumerate(values,1)})
            if result == 'all': value = [dict(row) for row in rows.mappings().all()]
            elif result == 'one':
                row = rows.mappings().first()
                value = dict(row) if row else None
            elif result == 'scalar': value = rows.scalar()
            else: value = None
            await session.commit()
            return value
    async def execute(self, query, *values): return await self._run(query, values, None)
    async def fetch(self, query, *values): return await self._run(query, values, 'all')
    async def fetchrow(self, query, *values): return await self._run(query, values, 'one')
    async def fetchval(self, query, *values): return await self._run(query, values, 'scalar')

class LegacyRepositoryOperations:

    async def update_order_paid_amount(self, order_id, amount_uah):
        await self.pool.execute('UPDATE orders SET paid_amount = COALESCE(paid_amount, 0.0) + $1 WHERE id = $2', float(amount_uah), order_id)

    async def add_to_blacklist(self, username: str):
        username = username.replace('@', '').strip()
        await self.pool.execute('INSERT INTO blacklist (username) VALUES ($1) ON CONFLICT DO NOTHING', username)

    async def remove_from_blacklist(self, username: str):
        username = username.replace('@', '').strip()
        await self.pool.execute('DELETE FROM blacklist WHERE username = $1', username)

    async def is_blacklisted(self, username: str):
        if not username:
            return False
        username = username.replace('@', '').strip()
        val = await self.pool.fetchval('SELECT 1 FROM blacklist WHERE username = $1', username)
        return bool(val)

    async def get_blacklist(self):
        rows = await self.pool.fetch('SELECT username FROM blacklist')
        return [row['username'] for row in rows]

    async def add_seat_ticket(self, event_id, row, seat, file_id, file_type):
        await self.pool.execute('\n            INSERT INTO seat_tickets (event_id, row_num, seat_num, file_id, file_type)\n            VALUES ($1, $2, $3, $4, $5)\n            ON CONFLICT (event_id, row_num, seat_num) \n            DO UPDATE SET file_id = EXCLUDED.file_id, file_type = EXCLUDED.file_type\n        ', event_id, str(row), str(seat), file_id, file_type)

    async def get_seat_ticket(self, event_id, row, seat):
        return await self.pool.fetchrow('SELECT file_id, file_type FROM seat_tickets WHERE event_id = $1 AND row_num = $2 AND seat_num = $3', event_id, str(row), str(seat))

    async def add_event(self, title, desc, photo_id, dt, venue_type, location, total_tickets, is_free, price, link, card, success_message, available_seats, has_promo, promocodes, promo_discount, generates_qr_ticket=False):
        query = '\n        INSERT INTO events (\n            title, description, photo_id, date_time, venue_type, location, \n            total_tickets, is_free, price, bank_link, card_number, success_message, \n            available_seats_list, has_promo, promocodes, promo_discount, generates_qr_ticket\n        ) \n        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)\n        '
        await self.pool.execute(query, title, desc, photo_id, dt, venue_type, location, total_tickets, is_free, price, link, card, success_message, available_seats, has_promo, promocodes, promo_discount, generates_qr_ticket)

    async def delete_event(self, event_id):
        await self.pool.execute('UPDATE events SET is_active = FALSE WHERE id = $1', event_id)

    async def update_event_field(self, event_id, field_name, new_value):
        allowed_fields = ['title', 'description', 'photo_id', 'date_time', 'location', 'total_tickets', 'price', 'bank_link', 'card_number', 'success_message']
        if field_name in allowed_fields:
            query = f'UPDATE events SET {field_name} = $1 WHERE id = $2'
            await self.pool.execute(query, new_value, event_id)

    async def update_user_field(self, tg_id: int, field_name: str, new_value: str):
        db_columns = {'last_name': 'last_name', 'first_name': 'first_name', 'institute': 'institute', 'group': 'student_group'}
        column = db_columns.get(field_name)
        if not column:
            return
        query = f'UPDATE users SET {column} = $1 WHERE telegram_id = $2'
        await self.pool.execute(query, new_value, tg_id)

    async def is_transaction_processed(self, tx_id: str):
        val = await self.pool.fetchval('SELECT 1 FROM processed_transactions WHERE tx_id = $1', tx_id)
        return bool(val)

    async def mark_transaction_processed(self, tx_id: str):
        await self.pool.execute('INSERT INTO processed_transactions (tx_id) VALUES ($1) ON CONFLICT DO NOTHING', tx_id)

    def get_full_hall_config(self, venue_type):
        all_ids = []
        if venue_type == 'organ_hall':
            rows = ['24', '23', '22', '21', '20', '19', '18', '17', '16', '15', '14', '13', '12Б', '12А', '12', '11', '10', '9', '8', '7', '6', '5Б', '5А', '5', '4', '3', '2', '1']
            for r in rows:
                count = 6 if r in ['13', '12Б', '12А', '12', '11', '10', '9', '8', '7', '6', '5Б', '5А', '5', '4', '3', '2', '1'] else 3
                for s in range(1, count * 2 + 1):
                    all_ids.append(f'{r}-{s}')
        return all_ids


class TicketRepository(LegacyRepositoryOperations):
    def __init__(self):
        self.pool = SQLAdapter()

    async def get_user(self, telegram_id):
        return await self.pool.fetchrow("SELECT *, telegram_id AS tg_id FROM users WHERE telegram_id = $1", telegram_id)

    async def get_all_users(self):
        return await self.pool.fetch("SELECT telegram_id AS tg_id FROM users")

    async def get_users_by_event(self, event_id):
        return await self.pool.fetch("SELECT DISTINCT user_id AS tg_id FROM orders WHERE event_id = $1 AND status = 'confirmed'", event_id)

    async def get_event(self, event_id):
        return await self.pool.fetchrow("""SELECT e.*, GREATEST(0, e.total_tickets - COALESCE(
            (SELECT SUM(ticket_count) FROM orders WHERE event_id=e.id AND status IN ('pending','pending_manual','confirmed')),0))
            AS remaining_tickets FROM events e WHERE e.id=$1""", event_id)

    async def get_active_events(self):
        return await self.pool.fetch("""SELECT e.*, GREATEST(0, e.total_tickets - COALESCE(
            (SELECT SUM(ticket_count) FROM orders WHERE event_id=e.id AND status IN ('pending','pending_manual','confirmed')),0))
            AS remaining_tickets FROM events e WHERE e.is_active=TRUE ORDER BY e.id DESC""")

    async def get_order(self, order_id):
        return await self.pool.fetchrow("SELECT * FROM orders WHERE id=$1", order_id)

    async def add_order(self, user_id, event_id, count, file_id=None, f_type=None, promocode=None, friends=None):
        keys = seat_keys(file_id) if f_type == "organ_seats" else []
        async with session_maker() as session:
            event = (await session.execute(text("SELECT * FROM events WHERE id=:id FOR UPDATE"), {"id":event_id})).mappings().first()
            if not event or not event["is_active"]:
                raise BookingError("Подія вже недоступна")
            event = dict(event)
            total = required_total(event, count, promocode)
            used = (await session.execute(text("SELECT COALESCE(SUM(ticket_count),0) FROM orders WHERE event_id=:id AND status IN ('pending','pending_manual','confirmed')"), {"id":event_id})).scalar()
            if used + count > event["total_tickets"]:
                raise BookingError("Ці квитки вже забронювали. Оберіть іншу кількість або місця")
            if event["venue_type"] in {"organ_hall", "assembly_hall"} and len(keys) != count:
                raise BookingError("Оберіть місця на схемі залу")
            allowed = seat_keys(event.get("available_seats_list"))
            if keys and not allowed:
                raise BookingError("Організатор має спочатку визначити доступні місця події")
            if allowed and not set(keys) <= set(allowed):
                raise BookingError("Вибрані місця не доступні для продажу")
            if keys:
                occupied = (await session.execute(text("SELECT seat_key FROM order_seats WHERE event_id=:id"), {"id":event_id})).scalars().all()
                if set(keys) & set(occupied):
                    raise BookingError("Одне з місць уже зайняте. Відкрийте схему знову")
            order_id = (await session.execute(text("""INSERT INTO orders
                (user_id,event_id,ticket_count,file_id,file_type,status,promocode,required_amount,friends)
                VALUES (:user_id,:event_id,:count,:file_id,:file_type,:status,:promo,:total,:friends) RETURNING id"""),
                {"user_id":user_id,"event_id":event_id,"count":count,"file_id":file_id,"file_type":f_type,
                 "status":"confirmed" if total == 0 else "pending", "promo":promocode,"total":total,"friends":json.dumps(friends or [],ensure_ascii=False)})).scalar_one()
            for key in keys:
                await session.execute(text("INSERT INTO order_seats(event_id,seat_key,order_id) VALUES (:event,:key,:order_id)"), {"event":event_id,"key":key,"order_id":order_id})
            await session.commit()
            return order_id

    async def update_order_status(self, order_id, status):
        if status not in {"pending", "pending_manual", "confirmed", "cancelled", "rejected"}:
            raise BookingError("Некоректний статус замовлення")
        async with session_maker() as session:
            row = (await session.execute(text("SELECT * FROM orders WHERE id=:id FOR UPDATE"), {"id":order_id})).mappings().first()
            if not row:
                raise BookingError("Замовлення не знайдено")
            if row["status"] in {"cancelled", "rejected"} and status not in {"cancelled", "rejected"}:
                raise BookingError("Замовлення вже скасоване; створіть нове бронювання")
            if row["status"] == "confirmed" and status != "confirmed":
                return False
            await session.execute(text("UPDATE orders SET status=:status WHERE id=:id"), {"status":status,"id":order_id})
            if status in {"cancelled", "rejected"}:
                await session.execute(text("DELETE FROM order_seats WHERE order_id=:id"), {"id":order_id})
            await session.commit()
            return row["status"] != status

    async def attach_proof_to_order(self, order_id, file_id, f_type):
        await self.pool.execute("""UPDATE orders SET proof_file_id=$1, proof_file_type=$2,
            status='pending_manual' WHERE id=$3 AND status IN ('pending','pending_manual')""", file_id, f_type, order_id)

    async def get_occupied_seats(self, event_id):
        event = await self.get_event(event_id)
        if not event:
            return []
        rows = await self.pool.fetch("SELECT seat_key FROM order_seats WHERE event_id=$1", event_id)
        occupied = {row["seat_key"] for row in rows}
        occupied.update(await sheets.get_occupied_from_sheet(event["title"], event["venue_type"]))
        if event.get("available_seats_list"):
            occupied.update(set(self.get_full_hall_config(event["venue_type"])) - set(seat_keys(event["available_seats_list"])))
        return sorted(occupied)

    async def get_seat_info(self, event_id, row, seat):
        return await self.pool.fetchrow("""SELECT o.id AS order_id,o.user_id,u.first_name,u.last_name,
            u.username,u.institute,u.student_group,o.file_id FROM orders o JOIN users u ON u.telegram_id=o.user_id
            JOIN order_seats s ON s.order_id=o.id WHERE o.event_id=$1 AND s.seat_key=$2""", event_id, f"{row}-{seat}")

    async def remove_seat_from_order(self, order_id, row, seat):
        key = f"{row}-{seat}"
        async with session_maker() as session:
            order = (await session.execute(text("SELECT * FROM orders WHERE id=:id FOR UPDATE"), {"id":order_id})).mappings().first()
            if not order:
                return False
            deleted = (await session.execute(text("DELETE FROM order_seats WHERE order_id=:id AND seat_key=:key RETURNING seat_key"), {"id":order_id,"key":key})).scalar()
            if not deleted:
                return False
            keys = [value for value in seat_keys(order["file_id"]) if value != key]
            await session.execute(text("UPDATE orders SET ticket_count=:count,file_id=:keys,status=:status WHERE id=:id"),
                {"count":len(keys),"keys":",".join(keys),"status":order["status"] if keys else "cancelled","id":order_id})
            await session.commit()
            return True


    def get_full_hall_config(self,venue_type):
        from app.features.ticketing.logic import hall_seats
        return hall_seats(venue_type)
