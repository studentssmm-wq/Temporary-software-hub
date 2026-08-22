import hmac
import hashlib
import json
import urllib.parse
from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel

from app.core.config import BOT_TOKEN
from app.features.users.user_repository import find_user_by_id
from app.features.payments.coin_service import process_coin_transaction

webapp_router = APIRouter(prefix="/api/webapp")


def verify_telegram_data(init_data: str) -> dict:
    """Перевіряє криптографічний підпис Telegram та повертає дані користувача."""
    try:
        parsed_data = dict(urllib.parse.parse_qsl(init_data))
        if "hash" not in parsed_data:
            raise ValueError("Відсутній хеш")

        hash_val = parsed_data.pop("hash")

        # Сортуємо ключі за алфавітом і формуємо рядок
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed_data.items()))

        # Створюємо секретний ключ з токена бота
        secret_key = hmac.new(
            b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()

        # Генеруємо наш хеш і порівнюємо з тим, що прислав Telegram
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if calculated_hash != hash_val:
            raise ValueError("Недійсний підпис")

        return json.loads(parsed_data["user"])
    except Exception as e:
        print(f"Помилка авторизації Web App: {e}")
        raise HTTPException(status_code=401, detail="Unauthorized")

# Схема для POST запиту на списання токенів


class SpendRequest(BaseModel):
    amount: int
    feature: str  # наприклад, 'tarot', 'fortune_cookie'


@webapp_router.get("/user")
async def get_user_data(request: Request, authorization: str = Header(None)):
    """Повертає баланс користувача для відображення у Web App"""
    if not authorization or not authorization.startswith("tma "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    init_data = authorization.split(" ", 1)[1]
    tg_user = verify_telegram_data(init_data)

    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        user = await find_user_by_id(session, tg_user["id"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found in DB")

        return {
            "telegram_id": user.telegram_id,
            "coins": user.coins,
            "first_name": user.first_name
        }


@webapp_router.post("/spend")
async def spend_coins(spend_data: SpendRequest, request: Request, authorization: str = Header(None)):
    """Списує токени за використання міні-гри"""
    if not authorization or not authorization.startswith("tma "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    init_data = authorization.split(" ", 1)[1]
    tg_user = verify_telegram_data(init_data)

    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        # Важливо: передаємо від'ємне значення для списання
        success = await process_coin_transaction(
            session=session,
            telegram_id=tg_user["id"],
            amount=-abs(spend_data.amount),
            feature=spend_data.feature
        )

        if not success:
            raise HTTPException(status_code=400, detail="Not enough coins")

        return {"status": "success", "message": "Coins deducted"}
