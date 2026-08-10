from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from app.keyboards.statistics_keyboard import get_deep_analytics_kb, get_time_spent_criteria_kb, get_portrait_criteria_kb, get_interval_criteria_kb, get_statistics_main_kb
from app.repositories.stats_repository import get_users_on_territory_count
from app.services.stats_service import (generate_historical_maximum_report, generate_audience_portrait_report, generate_outflow_dynamics_report,
                                        generate_loyalty_index_report, generate_scanner_workload_report, generate_time_spent_report, generate_traffic_peaks_report, get_audience_portrait)


from contextlib import suppress
from aiogram.exceptions import TelegramBadRequest
stats_router = Router()


@stats_router.callback_query(F.data == "stat_current")
async def show_count_on_site_handler(callback: CallbackQuery, session: AsyncSession):
    count = await get_users_on_territory_count(session)

    await callback.message.answer(f"📊 Зараз на території перебуває: {count} осіб.")
    await callback.answer()


@stats_router.callback_query(F.data == "stat_deep")
async def show_deep_analytics_handler(callback: CallbackQuery, session: AsyncSession):

    await callback.message.edit_text(
        "Глибока аналітика:",
        reply_markup=get_deep_analytics_kb()
    )
    await callback.answer()


@stats_router.callback_query(F.data == "stat_max")
async def show_historical_maximum_handler(callback: CallbackQuery, session: AsyncSession):
    answer = await generate_historical_maximum_report(session)
    await callback.message.edit_text(text=answer, parse_mode="HTML", reply_markup=get_deep_analytics_kb())
    await callback.answer()


@stats_router.callback_query(F.data == "stat_portrait")
async def ask_portrait_criteria_handler(callback: CallbackQuery):
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text="👥 <b>Оберіть, для якої аудиторії сформувати портрет:</b>",
            parse_mode="HTML",
            reply_markup=get_portrait_criteria_kb()
        )
    await callback.answer()


@stats_router.callback_query(F.data.in_(["stat_portrait_current", "stat_portrait_all"]))
async def show_portrait_report_handler(callback: CallbackQuery, session: AsyncSession):

    is_current = (callback.data == "stat_portrait_current")

    answer = await generate_audience_portrait_report(session, is_current=is_current)

    await callback.message.edit_text(
        text=answer,
        parse_mode="HTML",
        reply_markup=get_portrait_criteria_kb()
    )
    await callback.answer()


@stats_router.callback_query(F.data == "stat_traffic")
async def show_traffic_report_handler(callback: CallbackQuery, session: AsyncSession):

    # Викликаємо генерацію з жорстко заданим інтервалом 30
    answer = await generate_traffic_peaks_report(session, interval_minutes=30)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=answer,
            parse_mode="HTML",
            # Повертаємо головне меню глибокої аналітики
            reply_markup=get_deep_analytics_kb()
        )
    await callback.answer()


# --- ДИНАМІКА ВІДТОКУ (ВИХІД) ---

@stats_router.callback_query(F.data == "stat_outflow")
async def show_outflow_report_handler(callback: CallbackQuery, session: AsyncSession):

    # Викликаємо генерацію з жорстко заданим інтервалом 30
    answer = await generate_outflow_dynamics_report(session, interval_minutes=30)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=answer,
            parse_mode="HTML",
            # Повертаємо головне меню глибокої аналітики
            reply_markup=get_deep_analytics_kb()
        )
    await callback.answer()


@stats_router.callback_query(F.data == "stat_time")
async def ask_time_spent_criteria_handler(callback: CallbackQuery):
    """Показує меню вибору критерію для часу перебування"""
    await callback.message.edit_text(
        text="⏳ <b>Оберіть критерій для порівняння середнього часу перебування:</b>",
        parse_mode="HTML",
        reply_markup=get_time_spent_criteria_kb()
    )
    await callback.answer()


@stats_router.callback_query(F.data.in_(["stat_time_course", "stat_time_age", "stat_time_gender", "stat_time_institute"]))
async def show_time_spent_report_handler(callback: CallbackQuery, session: AsyncSession):
    """Генерує звіт по часу перебування залежно від обраної категорії"""

    # Визначаємо категорію на основі callback_data
    # (Якщо у вашій клавіатурі кнопка курсу/віку називається stat_time_course, ми мапимо її на "age")
    category_map = {
        "stat_time_course": "age",
        "stat_time_age": "age",
        "stat_time_gender": "gender",
        "stat_time_institute": "institute"
    }

    category = category_map.get(callback.data, "gender")

    answer = await generate_time_spent_report(session, group_by_category=category)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=answer,
            parse_mode="HTML",
            reply_markup=get_time_spent_criteria_kb()
        )
    await callback.answer()


@stats_router.callback_query(F.data == "stat_workload")
async def show_scanner_workload_handler(callback: CallbackQuery, session: AsyncSession):
    """Генерує звіт по завантаженості сканерів/волонтерів"""

    answer = await generate_scanner_workload_report(session, target_date=None)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=answer,
            parse_mode="HTML",
            reply_markup=get_deep_analytics_kb()
        )
    await callback.answer()


@stats_router.callback_query(F.data == "stat_loyalty")
async def show_loyalty_index_handler(callback: CallbackQuery, session: AsyncSession):
    """Генерує звіт по індексу лояльності (Retention Rate)"""

    answer = await generate_loyalty_index_report(session)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=answer,
            parse_mode="HTML",
            reply_markup=get_deep_analytics_kb()
        )
    await callback.answer()


@stats_router.callback_query(F.data == "stat_back_to_main")
async def back_to_stat_main_handler(callback: CallbackQuery):
    """Повертає з меню глибокої аналітики до головного меню статистики"""
    await callback.message.edit_text(
        text="📊 <b>Оберіть тип статистики:</b>",
        parse_mode="HTML",
        reply_markup=get_statistics_main_kb()
    )
    await callback.answer()
