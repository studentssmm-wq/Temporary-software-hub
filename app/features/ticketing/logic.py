"""Pure validation and money calculations, independent of Telegram and PostgreSQL."""
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

ACTIVE_ORDER_STATUSES = ("pending", "pending_manual", "confirmed")

class BookingError(ValueError):
    pass


def amount(value) -> Decimal:
    try:
        result = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise BookingError("Некоректна сума") from None
    if not result.is_finite() or result < 0:
        raise BookingError("Сума має бути додатною або нульовою")
    return result


def unit_price(value) -> Decimal:
    match = re.search(r"\d+(?:[.,]\d{1,2})?", str(value))
    if not match:
        raise BookingError("Для платної події потрібно вказати ціну")
    return amount(match.group().replace(",", "."))


def required_total(event, quantity: int, promo=None) -> Decimal:
    if not isinstance(quantity, int) or isinstance(quantity, bool) or not 1 <= quantity <= 50:
        raise BookingError("Кількість квитків має бути від 1 до 50")
    if event["is_free"]:
        return Decimal("0.00")
    discount = Decimal("0")
    if promo:
        allowed = {x.strip().upper() for x in (event.get("promocodes") or "").split(",") if x.strip()}
        if not event.get("has_promo") or promo.strip().upper() not in allowed:
            raise BookingError("Промокод не діє")
        discount = amount(event.get("promo_discount") or 0)
    return amount(max(Decimal("0"), unit_price(event["price"]) - discount) * quantity)


def seat_keys(value: str | None) -> list[str]:
    if not value:
        return []
    keys = [part.strip() for part in value.split(",")]
    if len(keys) != len(set(keys)) or any(not re.fullmatch(r"[^,|\x00-\x1f]{1,80}-[^,|\x00-\x1f]{1,20}", key) for key in keys):
        raise BookingError("Некоректні або повторені місця")
    return keys


def payment_reference(text: str):
    match = re.search(r"(?<![A-Z0-9])NULP-(\d+)(?![A-Z0-9])", text.upper())
    return int(match.group(1)) if match else None


def hall_seats(venue_type: str) -> list[str]:
    if venue_type == "organ_hall":
        rows=["24","23","22","21","20","19","18","17","16","15","14","13","12Б","12А","12","11","10","9","8","7","6","5Б","5А","5","4","3","2","1"]
        small={str(number) for number in range(14,25)}
        return [f"{row}-{seat}" for row in rows for seat in range(1,7 if row in small else 13)]
    if venue_type == "assembly_hall":
        keys=[f"{zone}-{row}-{seat}" for zone in ["A","B","C"] for row in range(2,24) for seat in range(1,9)]
        keys += [f"D-24-{seat}" for seat in range(1,27)]
        keys += [f"D-{row}-{seat}" for row in range(25,29) for seat in range(1,21)]
        keys += [f"{zone}-{row}-{seat}" for zone in ["ЛБ","ПБ"] for row in range(1,20) for seat in range(1,4)]
        keys += [f"Балкон-{row}-{seat}" for row,count in enumerate([26,29,28,29,30,33],1) for seat in range(1,count+1)]
        return keys
    return []
