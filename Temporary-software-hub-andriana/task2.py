import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАЛАШТУВАННЯ ---
BOT_TOKEN = "8938895089:AAEK-BcHUj5muyVbb4rlMoLUjhP9GJYUbNg"  # Твій токен

router = Router()


# --- СТЕЙТИ (Кроки реєстрації) ---
class Registration(StatesGroup):
    full_name = State()
    institute = State()
    non_student_role = State()
    group = State()
    gender = State()
    birth_date = State()
    consent = State()


# --- ГЕНЕРАЦІЯ КЛАВІАТУР ---

# 1. Клавіатура інститутів (за алфавітом)
def get_institutes_kb():
    institutes = sorted([
        "ІНЕМ", "ІППО", "ІКТА", "ІКНІ", "ІКТЕ", "ІМФН", "ІГСН",
        "ІГДГ", "ІПМТ", "ІМІТ", "ІАРД", "ІЕСК", "ІХХТ", "ІБІБ", "ІВБІ", "ІППТ"
    ])
    builder = InlineKeyboardBuilder()
    for inst in institutes:
        builder.button(text=inst, callback_data=f"inst_{inst}")

    # Вирівнюємо кнопки по 3 в ряд
    builder.adjust(3)
    # Додаємо кнопку "Не студент" окремо знизу зі смайликом
    builder.row(types.InlineKeyboardButton(text="Не студент🙅‍♂️", callback_data="inst_Не студент"))
    return builder.as_markup()


# 2. Клавіатура для ролі не студента зі смайликами
non_student_kb = types.InlineKeyboardMarkup(inline_keyboard=[
    [types.InlineKeyboardButton(text="Викладач👨‍🏫", callback_data="role_Викладач")],
    [types.InlineKeyboardButton(text="Школяр👦", callback_data="role_Школяр")],
    [types.InlineKeyboardButton(text="Батьки👨👩", callback_data="role_Батьки")],
    [types.InlineKeyboardButton(text="Інше", callback_data="role_Інше")]
])

# 3. Клавіатура статі
gender_kb = types.InlineKeyboardMarkup(inline_keyboard=[
    [types.InlineKeyboardButton(text="Чоловіча", callback_data="gender_Чоловіча"),
     types.InlineKeyboardButton(text="Жіноча", callback_data="gender_Жіноча")]
])

# 4. Клавіатура згоди
consent_kb = types.InlineKeyboardMarkup(inline_keyboard=[
    [types.InlineKeyboardButton(text="Так, дозволяю", callback_data="consent_Так"),
     types.InlineKeyboardButton(text="Ні, не дозволяю", callback_data="consent_Ні")]
])


# --- ХЕНДЛЕРИ ---

# КРОК 1: /start -> Невидимий збір даних та запит ПІБ
@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    # Збираємо ID та тег
    await state.update_data(
        telegram_id=message.from_user.id,
        telegram_tag=message.from_user.username or "Без тегу"
    )
    # Питаємо ПІБ одним повідомленням
    await message.answer(
        "Привіт! Починаємо реєстрацію.\nБудь ласка, введи свій ПІБ:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(Registration.full_name)


# КРОК 2: ПІБ -> Запит Інституту (Кнопочки)
@router.message(Registration.full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    text = message.text.strip()

    # Захист від дурачка: перевіряємо, щоб було мінімум 2 слова
    if len(text.split()) < 2:
        await message.answer("Будь ласка, введи повний ПІБ (мінімум Прізвище та Ім'я через пробіл):")
        return

    # Робимо кожне слово з великої літери (іванов іван -> Іванов Іван)
    formatted_name = " ".join(word.capitalize() for word in text.split())

    await state.update_data(full_name=formatted_name)
    await message.answer("Чудово! Обери свій інститут (або вкажи, що ти не студент):", reply_markup=get_institutes_kb())
    await state.set_state(Registration.institute)


# КРОК 3: Інститут (Колбек) -> Розгалуження (Група або Хто ти)
@router.callback_query(Registration.institute, F.data.startswith("inst_"))
async def process_institute(callback: types.CallbackQuery, state: FSMContext):
    institute_name = callback.data.split("_")[1]

    if institute_name == "Не студент":
        await callback.message.edit_text("Оскільки ти не студент, обери, хто ти:", reply_markup=non_student_kb)
        # Ставимо прочерк замість інституту ТА групи для не-студентів
        await state.update_data(institute="-", group="-")
        await state.set_state(Registration.non_student_role)
    else:
        await callback.message.edit_text(f"Обрано інститут: {institute_name}\n\nНапиши свою групу (наприклад, ОІ-12):")
        # Зберігаємо інститут і статус "Студент"
        await state.update_data(institute=institute_name, non_student_role="Студент")
        await state.set_state(Registration.group)

    await callback.answer()


# КРОК 4А: Група (для студентів) -> Запит статі
@router.message(Registration.group)
async def process_group(message: types.Message, state: FSMContext):
    await state.update_data(group=message.text.upper())
    await message.answer("Обери свою стать:", reply_markup=gender_kb)
    await state.set_state(Registration.gender)


# КРОК 4Б: Роль не студента (Колбек) -> Запит статі
@router.callback_query(Registration.non_student_role, F.data.startswith("role_"))
async def process_non_student_role(callback: types.CallbackQuery, state: FSMContext):
    role = callback.data.split("_")[1]
    await state.update_data(non_student_role=role)
    await callback.message.edit_text(f"Твій статус: {role}\n\nОбери свою стать:", reply_markup=gender_kb)
    await state.set_state(Registration.gender)


# КРОК 5: Стать (Колбек) -> Запит дати народження
@router.callback_query(Registration.gender, F.data.startswith("gender_"))
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    gender_name = callback.data.split("_")[1]
    await state.update_data(gender=gender_name)
    await callback.message.edit_text(
        f"Стать: {gender_name}\n\nТепер напиши свою дату народження у форматі DD.MM.YYYY (наприклад, 14.11.2006):"
    )
    await state.set_state(Registration.birth_date)


# КРОК 6: Дата народження -> Запит згоди
@router.message(Registration.birth_date)
async def process_birth_date(message: types.Message, state: FSMContext):
    try:
        valid_date = datetime.strptime(message.text, "%d.%m.%Y")
        if valid_date.year < 1900 or valid_date.year > 2026:
            await message.answer("Рік виглядає підозріло 👀 Введи реальну дату:")
            return
    except ValueError:
        await message.answer("Ой, формат неправильний. ❌ Напиши дату ось так: 14.11.2006")
        return

    await state.update_data(birth_date=message.text)
    await message.answer("Останній крок! Чи даєш ти згоду на обробку персональних даних?", reply_markup=consent_kb)
    await state.set_state(Registration.consent)


# КРОК 7: Згода (Колбек) -> Фінал і База Даних
@router.callback_query(Registration.consent, F.data.startswith("consent_"))
async def process_consent(callback: types.CallbackQuery, state: FSMContext):
    consent = callback.data.split("_")[1]
    await state.update_data(consent=consent)

    # ЗБИРАЄМО ВСІ ДАНІ З БЛОКНОТУ
    data = await state.get_data()

    summary = (
        "🎉 Реєстрація успішна! Усі дані зібрано:\n\n"
        f"🆔 Telegram ID: {data['telegram_id']}\n"
        f"👤 Тег: @{data['telegram_tag']}\n"
        f"📝 ПІБ: {data['full_name']}\n"
        f"🎓 Інститут: {data['institute']}\n"
        f"👥 Статус: {data['non_student_role']}\n"
        f"📚 Група: {data['group']}\n"
        f"⚧ Стать: {data['gender']}\n"
        f"🎂 Дата народження: {data['birth_date']}\n"
        f"🔐 Згода на обробку: {data['consent']}"
    )

    await callback.message.edit_text(summary)
    await state.clear()


# --- АНТИ-ДУРАК ДЛЯ ІНЛАЙН КНОПОК ---
@router.message(Registration.institute)
@router.message(Registration.non_student_role)
@router.message(Registration.gender)
@router.message(Registration.consent)
async def ignore_text_input(message: types.Message):
    await message.answer("Будь ласка, скористайся кнопками вище 👆")


# --- ЗАПУСК БОТА ---
async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(router)

    print("Бот запущено! Йди в Telegram і пиши /start")
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())