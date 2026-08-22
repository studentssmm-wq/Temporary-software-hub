from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.analytics.stats_repository import (
    get_historical_maximum,
    get_audience_portrait,
    get_traffic_peaks,
    get_outflow_dynamics,
    get_average_time_spent,
    get_scanner_workload,
    get_loyalty_index
)


async def generate_historical_maximum_report(session: AsyncSession) -> str:
    """Формує звіт про історичний максимум (одночасне перебування)."""
    # За замовчуванням рахуємо по 30 хв (можна змінити)
    peaks = await get_historical_maximum(session, interval_minutes=30)

    if not peaks:
        return "🤷‍♂️ Наразі немає даних для розрахунку максимуму."

    report = f"🏆 <b>Історичний максимум (Одночасно на локації):</b>\n\n"
    for i, (time_window, count) in enumerate(peaks[:5], start=1):
        report += f"<b>Топ {i}:</b> {time_window} ➡️ <b>{count} осіб</b>\n"

    return report


async def generate_audience_portrait_report(session: AsyncSession, is_current: bool) -> str:
    """Формує глибоку аналітику аудиторії з відсотками."""
    data = await get_audience_portrait(session, is_current)

    if data.get("total", 0) == 0:
        return "🤷‍♂️ Наразі немає даних для формування портрету аудиторії."

    total = data["total"]
    avg_age = data["average_age"]

    report = f"📊 <b>Портрет аудиторії</b> "
    report += "(Зараз на локації):\n\n" if is_current else "(За весь час):\n\n"

    report += f"👥 <b>Всього людей:</b> {total}\n"
    report += f"🎂 <b>Середній вік:</b> {avg_age} років\n\n"

    report += "🚻 <b>Стать:</b>\n"
    for gender, count in data["gender"].items():
        percent = round((count / total) * 100, 1)
        report += f"• {gender}: {count} ({percent}%)\n"

    report += "\n🎓 <b>Статус:</b>\n"
    for status, count in data["status"].items():
        percent = round((count / total) * 100, 1)
        report += f"• {status}: {count} ({percent}%)\n"

    if data["institute"]:
        report += "\n🏛 <b>Інститути:</b>\n"
        sorted_inst = sorted(data["institute"].items(),
                             key=lambda x: x[1], reverse=True)
        for inst, count in sorted_inst:
            percent = round((count / total) * 100, 1)
            report += f"• {inst}: {count} ({percent}%)\n"

    return report


async def generate_traffic_peaks_report(session: AsyncSession, interval_minutes: int = 30) -> str:
    peaks_by_day = await get_traffic_peaks(session, interval_minutes)

    if not peaks_by_day:
        return "🤷‍♂️ Наразі немає даних про входи."

    report = f"📈 <b>Топ піків завантаженості (ВХІД):</b>\n"

    for date_str, peaks in peaks_by_day.items():
        report += f"📅 <b>{date_str}</b>\n"
        # Беремо тільки Топ-3 для конкретного дня
        for i, (time_window, count) in enumerate(peaks[:3], start=1):
            report += f"  <b>Топ {i}:</b> {time_window} ➡️ <b>{count} осіб</b>\n"
        report += "\n"

    return report.strip()


async def generate_outflow_dynamics_report(session: AsyncSession, interval_minutes: int = 30) -> str:
    peaks_by_day = await get_outflow_dynamics(session, interval_minutes)

    if not peaks_by_day:
        return "🤷‍♂️ Наразі немає даних про виходи з локації."

    report = f"🏃‍♂️ <b>Динаміка масового відтоку (ВИХІД):</b>\n"

    for date_str, peaks in peaks_by_day.items():
        report += f"📅 <b>{date_str}</b>\n"
        # Беремо тільки Топ-3 для конкретного дня
        for i, (time_window, count) in enumerate(peaks[:3], start=1):
            report += f"  <b>Топ {i}:</b> {time_window} ➡️ <b>{count} осіб</b>\n"
        report += "\n"

    return report.strip()


async def generate_time_spent_report(session: AsyncSession, group_by_category: str) -> str:
    data = await get_average_time_spent(session, group_by_category)
    if not data:
        return "🤷‍♂️ Наразі немає завершених сесій для підрахунку."

    labels = {"gender": "Статтю", "institute": "Інститутами", "age": "Віком"}
    label = labels.get(group_by_category, "Категоріями")

    # Вираховуємо загальну кількість візитів для відсотків
    total_visits = sum(info["visits"] for info in data.values())

    report = f"⏳ <b>Середній час перебування:</b>\n<i>(Розбивка за {label.lower()})</i>\n\n"

    for i, (cat, info) in enumerate(data.items(), start=1):
        minutes = info["minutes"]
        visits = info["visits"]

        # Рахуємо відсоток цієї категорії від загальної маси відвідувачів
        percent = round((visits / total_visits) * 100,
                        1) if total_visits > 0 else 0

        hours = minutes // 60
        mins = minutes % 60
        time_str = f"{hours} год {mins} хв" if hours > 0 else f"{mins} хв"

        report += f"{i}. <b>{cat}</b>: {time_str} <i>({percent}% аудиторії)</i>\n"

    return report


async def generate_scanner_workload_report(session: AsyncSession, target_date: date | None = None) -> str:
    """Аналізує ефективність волонтерів-сканерів."""
    workload = await get_scanner_workload(session, target_date)
    if not workload:
        return "🤷‍♂️ Жоден квиток ще не був просканований."

    date_str = f" за {target_date.strftime('%d.%m.%Y')}" if target_date else " за весь час"
    report = f"📊 <b>Завантаженість входів/волонтерів{date_str}:</b>\n\n"

    total_scans = sum(count for _, _, count in workload)

    for i, (fname, lname, count) in enumerate(workload, start=1):
        name = f"{fname} {lname or ''}".strip()
        percent = round((count / total_scans) * 100, 1)
        report += f"{i}. 👤 {name} ➡️ <b>{count} скан.</b> ({percent}%)\n"

    return report


async def generate_loyalty_index_report(session: AsyncSession) -> str:
    """Формує звіт по індексу лояльності з емоційною оцінкою."""
    loyal_users, loyalty_percent = await get_loyalty_index(session)

    if loyalty_percent >= 50:
        status = "🔥 Неймовірний успіх! Більшість повертається."
    elif loyalty_percent >= 30:
        status = "👍 Хороший результат, аудиторія зацікавлена."
    elif loyalty_percent > 0:
        status = "🤔 Поки що низький, треба більше інтерактиву."
    else:
        status = "🤷‍♂️ Даних поки недостатньо."

    return (
        f"💛 <b>Індекс лояльності (Retention Rate): {loyalty_percent}%</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Кількість відвідувачів, які приходили у 2 або більше різних днів: <b>{loyal_users}</b>.\n\n"
        f"<b>Оцінка:</b> {status}"
    )
