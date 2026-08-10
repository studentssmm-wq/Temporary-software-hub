
from datetime import date
from sqlalchemy import func, select, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from app.database.models import QRPass, ScanLog, User


async def get_users_on_territory_count(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count(QRPass.telegram_id)).where(
            QRPass.is_on_territory == True)
    )
    return result.scalar_one()


async def get_historical_maximum(session: AsyncSession) -> int:
    """Рахує скільки унікальних людей відвідало подію за весь час."""
    result = await session.execute(
        select(func.count(func.distinct(ScanLog.telegram_id)))
        .where(ScanLog.action_type == "in")
    )
    return result.scalar() or 0


async def get_audience_portrait(session: AsyncSession, is_current: bool):
    stmt = select(User.gender, User.institute,
                  User.birth_date,  User.non_student_type)

    if is_current:
        stmt = stmt.join(QRPass, QRPass.telegram_id == User.telegram_id).where(
            QRPass.is_on_territory == True)
    result = await session.execute(stmt)
    users_data = result.all()
    total = len(users_data)
    if total == 0:
        return {"total": 0}

    portrait = {
        "total": total,
        "gender": {},
        "institute": {},
        "status": {"Студенти": 0, "Інші": 0},
        "average_age": 0
    }
    total_age = 0
    today = date.today()

    for gender, institute, birth_date, non_student_type in users_data:
        # Рахуємо стать
        portrait["gender"][gender] = portrait["gender"].get(gender, 0) + 1

        # Рахуємо інститути (тільки якщо вказано)
        if institute:
            portrait["institute"][institute] = portrait["institute"].get(
                institute, 0) + 1

        # Рахуємо статус (якщо є non_student_type — значить не студент)
        if non_student_type:
            portrait["status"]["Інші"] += 1
        else:
            portrait["status"]["Студенти"] += 1

        # Вираховуємо вік (сьогоднішній рік мінус рік народження, враховуючи місяць і день)
        if birth_date:
            if isinstance(birth_date, str):
                birth_date = date.fromisoformat(birth_date[:10])

            age = today.year - birth_date.year - \
                ((today.month, today.day) < (birth_date.month, birth_date.day))
            total_age += age

    # Вираховуємо середній вік і округлюємо до 1 знака після коми
    portrait["average_age"] = round(total_age / total, 1)

    return portrait


async def get_traffic_peaks(session: AsyncSession, interval_minutes: int = 60) -> list[tuple[str, int]]:
    # 1. Витягуємо всі часові мітки для входів
    stmt = select(ScanLog.scanned_at).where(ScanLog.action_type == "in")
    result = await session.execute(stmt)
    timestamps = result.scalars().all()

    if not timestamps:
        return []

    traffic = {}

    for ts in timestamps:
        minute_block = (ts.minute // interval_minutes) * interval_minutes

        block_start = ts.replace(minute=minute_block, second=0, microsecond=0)
        block_end = block_start + timedelta(minutes=interval_minutes)

        time_window = f"{block_start.strftime('%d.%m %H:%M')} - {block_end.strftime('%H:%M')}"

        traffic[time_window] = traffic.get(time_window, 0) + 1

    sorted_peaks = sorted(traffic.items(), key=lambda x: x[1], reverse=True)

    return sorted_peaks


async def get_outflow_dynamics(session: AsyncSession, interval_minutes: int = 60):
    stmt = select(ScanLog.scanned_at).where(ScanLog.action_type == "out")
    result = await session.execute(stmt)
    timestamps = result.scalars().all()

    if not timestamps:
        return []

    traffic = {}

    for ts in timestamps:
        minute_block = (ts.minute // interval_minutes) * interval_minutes

        block_start = ts.replace(minute=minute_block, second=0, microsecond=0)
        block_end = block_start + timedelta(minutes=interval_minutes)

        time_window = f"{block_start.strftime('%d.%m %H:%M')} - {block_end.strftime('%H:%M')}"

        traffic[time_window] = traffic.get(time_window, 0) + 1

    sorted_peaks = sorted(traffic.items(), key=lambda x: x[1], reverse=True)

    return sorted_peaks


async def get_average_time_spent(session: AsyncSession, group_by_category: str) -> dict:

    stmt = select(
        ScanLog.telegram_id,
        ScanLog.action_type,
        ScanLog.scanned_at,
        User.gender,
        User.institute,
        User.birth_date
    ).join(
        User, User.telegram_id == ScanLog.telegram_id
    ).order_by(
        ScanLog.telegram_id, ScanLog.scanned_at
    )

    result = await session.execute(stmt)
    logs = result.all()

    in_times = {}
    category_stats = {}
    today = date.today()

    for t_id, action, scanned_at, gender, institute, birth_date in logs:

        if group_by_category == "gender":
            cat_key = gender
        elif group_by_category == "institute":
            cat_key = institute or "Не вказано"
        elif group_by_category == "age":
            if birth_date:
                if isinstance(birth_date, str):
                    birth_date = date.fromisoformat(birth_date[:10])

                age = today.year - birth_date.year - \
                    ((today.month, today.day) < (birth_date.month, birth_date.day))
                cat_key = f"{age} років"
            else:
                cat_key = "Вік невідомий"
        else:
            cat_key = "Всі"

        if cat_key not in category_stats:
            category_stats[cat_key] = {"seconds": 0, "visits": 0}

        if action == "in":
            in_times[t_id] = scanned_at
        elif action == "out" and t_id in in_times:
            time_in = in_times.pop(t_id)
            duration = (scanned_at - time_in).total_seconds()

            category_stats[cat_key]["seconds"] += duration
            category_stats[cat_key]["visits"] += 1

    averages = {}
    for cat, stats in category_stats.items():
        if stats["visits"] > 0:
            avg_seconds = stats["seconds"] / stats["visits"]
            averages[cat] = round(avg_seconds / 60)

    sorted_averages = dict(
        sorted(averages.items(), key=lambda item: item[1], reverse=True))

    return sorted_averages


async def get_scanner_workload(session: AsyncSession, target_date: date | None = None):
    stmt = select(
        User.first_name,
        User.last_name,
        func.count(ScanLog.id).label("scan_count")
    ).join(
        User, User.telegram_id == ScanLog.scanner_id
    )

    if target_date:
        stmt = stmt.where(cast(ScanLog.scanned_at, Date) == target_date)

    stmt = stmt.group_by(
        User.telegram_id, User.first_name, User.last_name
    ).order_by(
        func.count(ScanLog.id).desc()
    )

    result = await session.execute(stmt)

    return result.all()


async def get_loyalty_index(session: AsyncSession) -> float:
    """
    Рахує відсоток користувачів, які відвідували подію у більше ніж один унікальний день.
    Повертає число (float) від 0.0 до 100.0.
    """
    stmt = select(
        ScanLog.telegram_id,
        func.count(func.distinct(cast(ScanLog.scanned_at, Date))
                   ).label("days_visited")
    ).where(
        ScanLog.action_type == "in"
    ).group_by(
        ScanLog.telegram_id
    )

    result = await session.execute(stmt)
    users_visits = result.all()

    total_users = len(users_visits)

    if total_users == 0:
        return 0, 0.0

    loyal_users = sum(
        1 for user_id, days_visited in users_visits if days_visited > 1)

    loyalty_index = (loyal_users / total_users) * 100

    return loyal_users, round(loyalty_index, 2)
