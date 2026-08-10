from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_statistics_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="💛 Зараз на локації", callback_data="stat_current"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🖤 Глибока аналітика", callback_data="stat_deep"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад", callback_data="admin_cancel"
        )
    )

    return builder.as_markup()


def get_deep_analytics_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="💛 Історичний максимум", callback_data="stat_max"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🖤 Портрет аудиторії", callback_data="stat_portrait"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💛 Трафік та Піки", callback_data="stat_traffic"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🖤 Динаміка відтоку", callback_data="stat_outflow"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💛 Час перебування", callback_data="stat_time"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🖤 Завантаженість входів", callback_data="stat_workload"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💛 Індекс лояльності", callback_data="stat_loyalty"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад", callback_data="stat_back_to_main"
        )
    )

    return builder.as_markup()


def get_time_spent_criteria_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="🎓 За віком", callback_data="stat_time_course"
        ),
        InlineKeyboardButton(
            text="🚻 За статтю", callback_data="stat_time_gender"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🏛 За інститутом", callback_data="stat_time_institute"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад", callback_data="stat_deep"
        )
    )

    return builder.as_markup()


def get_portrait_criteria_kb() -> InlineKeyboardMarkup:
    """Підменю для вибору типу аудиторії для портрета"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📍 Зараз на локації", callback_data="stat_portrait_current"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🌍 За весь час", callback_data="stat_portrait_all"
        )
    )
    builder.row(
        # Повертає на Рівень 2 (Глибока аналітика)
        InlineKeyboardButton(
            text="🔙 Назад", callback_data="stat_deep"
        )
    )

    return builder.as_markup()


def get_interval_criteria_kb(report_type: str) -> InlineKeyboardMarkup:
    """
    Підменю для вибору часового інтервалу.
    report_type має бути "traffic" або "outflow".
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="⏱ 15 хвилин", callback_data=f"stat_{report_type}_15"
        ),
        InlineKeyboardButton(
            text="⏱ 30 хвилин", callback_data=f"stat_{report_type}_30"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🕒 1 година", callback_data=f"stat_{report_type}_60"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад", callback_data="stat_deep"
        )
    )

    return builder.as_markup()
