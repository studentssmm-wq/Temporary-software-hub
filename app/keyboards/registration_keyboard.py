from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_institutes_kb() -> types.InlineKeyboardMarkup:
    institutes = sorted([
        "ІНЕМ", "ІППО", "ІКТА", "ІКНІ", "ІКТЕ", "ІМФН", "ІГСН",
        "ІГДГ", "ІПМТ", "ІМІТ", "ІАРД", "ІЕСК", "ІХХТ", "ІБІБ", "ІВБІ", "ІППТ"
    ])
    builder = InlineKeyboardBuilder()
    for inst in institutes:
        builder.button(text=inst, callback_data=f"inst_{inst}")

    builder.adjust(3)
    builder.row(types.InlineKeyboardButton(
        text="Не студент🙅‍♂️", callback_data="inst_Не студент"))
    return builder.as_markup()


non_student_kb = types.InlineKeyboardMarkup(inline_keyboard=[
    [types.InlineKeyboardButton(
        text="Викладач👨‍🏫", callback_data="role_Викладач")],
    [types.InlineKeyboardButton(text="Школяр👦", callback_data="role_Школяр")],
    [types.InlineKeyboardButton(text="Батьки👨👩", callback_data="role_Батьки")],
    [types.InlineKeyboardButton(text="Інше", callback_data="role_Інше")]
])

gender_kb = types.InlineKeyboardMarkup(inline_keyboard=[
    [types.InlineKeyboardButton(text="Чоловіча", callback_data="gender_Чоловіча"),
     types.InlineKeyboardButton(text="Жіноча", callback_data="gender_Жіноча")]
])

consent_kb = types.InlineKeyboardMarkup(inline_keyboard=[
    [types.InlineKeyboardButton(text="Так, дозволяю", callback_data="consent_Так"),
     types.InlineKeyboardButton(text="Ні, не дозволяю", callback_data="consent_Ні")]
])
