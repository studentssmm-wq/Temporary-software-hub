import uuid
from io import BytesIO
import segno
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.qr_pass.qr_repository import create_pass, get_pass_by_user, toggle_pass, get_pass
from app.core.models import QRPass
from app.core.redis_client import redis_client


def generate_pass_id() -> uuid.UUID:
    return uuid.uuid4()


def generate_qr(pass_id: uuid.UUID) -> BytesIO:
    deep_link = (
        f"https://t.me/students_nulp_official_bot"
        f"?start={pass_id}"
    )

    qrcode = segno.make(deep_link)
    qr_file = BytesIO()
    qrcode.save(qr_file, kind="png", scale=10)
    qr_file.seek(0)
    return qr_file


async def create_qr_pass(session: AsyncSession, telegram_id: int):
    existing_pass = await get_pass_by_user(session, telegram_id)
    if existing_pass:
        pass_id = existing_pass.pass_id
        qrcode = generate_qr(pass_id)

        return pass_id, qrcode

    pass_id = generate_pass_id()

    await create_pass(
        session,
        pass_id,
        telegram_id,
    )
    qrcode = generate_qr(pass_id)

    return pass_id, qrcode


async def process_pass_scan(
    session: AsyncSession,
    pass_id: UUID,
    scanner_id: int,
) -> tuple[dict | None, bool]:
    
    pass_id_str = str(pass_id)
    cache_key = f"qr_pass:{pass_id_str}"
    
    # 1. Шукаємо статус перепустки в пам'яті Redis
    cached_data = await redis_client.get(cache_key)
    
    if cached_data:
        pass_data = json.loads(cached_data)
    else:
        # 2. Якщо в кеші нема (наприклад, після рестарту), йдемо в БД
        qr_pass = await get_pass(session, pass_id)
        if not qr_pass:
            return None, False
        
        pass_data = {
            "telegram_id": qr_pass.telegram_id,
            "is_on_territory": qr_pass.is_on_territory
        }
    
    was_on_territory = pass_data["is_on_territory"]
    now_on_territory = not was_on_territory
    action = "in" if now_on_territory else "out"
    
    # 3. Оновлюємо статус у Redis миттєво (кешуємо на 24 години)
    pass_data["is_on_territory"] = now_on_territory
    await redis_client.set(cache_key, json.dumps(pass_data), ex=86400)
    
    # 4. Закидаємо лог у чергу Redis ЗАМІСТЬ бази даних
    kyiv_time = datetime.now(ZoneInfo("Europe/Kyiv")).isoformat()
    log_entry = {
        "telegram_id": pass_data["telegram_id"],
        "scanner_id": scanner_id,
        "action_type": action,
        "scanned_at": kyiv_time,
        "pass_id": pass_id_str
    }
    await redis_client.rpush("scan_logs_queue", json.dumps(log_entry))
    
    # Повертаємо словник замість ORM-об'єкта (хендлер з qr_handler.py обробить це коректно)
    return pass_data, was_on_territory
