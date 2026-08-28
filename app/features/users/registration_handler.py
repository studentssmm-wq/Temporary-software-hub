from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.users.registration_states import Registration
from app.features.users.registration_keyboard import get_institutes_kb, non_student_kb, gender_kb, consent_kb
from app.features.users.user_repository import create_user
from app.shared.main_keyboard import get_main_menu_kb
registration_router = Router()

# КРОК 1: /register або /start
@registration_router.message(Command("register"))
async def cmd_register(message: types.Message, state: FSMContext):
    await state.update_data(
        telegram_id=message.from_user.id,
        telegram_tag=message.from_user.username
    )
    
    # Створюємо клавіатуру для запиту контакту
    contact_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поділитися номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await message.answer(
        "Привіт! Починаємо реєстрацію.\nДля початку, будь ласка, натисни кнопку нижче, щоб поділитися номером телефону:",
        reply_markup=contact_kb
    )
    await state.set_state(Registration.phone_number)

# КРОК 2: Збереження номера телефону
@registration_router.message(Registration.phone_number, F.contact)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone_number=phone)

    # Прибираємо клавіатуру з номером і просимо ПІБ
    await message.answer(
        "Дякую! Тепер введи своє Прізвище та Ім'я:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Registration.full_name)

# КРОК 3: ПІБ (Колишній Крок 2)
@registration_router.message(Registration.full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if len(text.split()) < 2:
        await message.answer("Будь ласка, введи Прізвище та Ім'я через пробіл:")
        return

    formatted_name = " ".join(word.capitalize() for word in text.split())
    await state.update_data(full_name=formatted_name)
    await message.answer("Чудово! Обери свій інститут (або вкажи, що ти не студент):", reply_markup=get_institutes_kb())
    await state.set_state(Registration.institute)

# КРОК 3: Інститут


@registration_router.callback_query(Registration.institute, F.data.startswith("inst_"))
async def process_institute(callback: types.CallbackQuery, state: FSMContext):
    institute_name = callback.data.split("_")[1]
    if institute_name == "Не студент":
        await callback.message.edit_text("Оскільки ти не студент, обери, хто ти:", reply_markup=non_student_kb)
        await state.update_data(institute=None, group=None)
        await state.set_state(Registration.non_student_role)
    else:
        # await callback.message.edit_text(f"Обрано інститут: {institute_name}\n\nНапиши свою групу (наприклад, ОІ-12):")
        # await state.update_data(institute=institute_name, non_student_role=None)
        # await state.set_state(Registration.group)

        await callback.message.edit_text(f"Обрано інститут: {institute_name}\n\nОбери свою стать:", reply_markup=gender_kb)
        await state.update_data(institute=institute_name, non_student_role=None, group=None)
        await state.set_state(Registration.gender)
    await callback.answer()

# КРОК 4А: Група


# @registration_router.message(Registration.group)
# async def process_group(message: types.Message, state: FSMContext):
#     await state.update_data(group=message.text.upper())
#     await message.answer("Обери свою стать:", reply_markup=gender_kb)
#     await state.set_state(Registration.gender)

# КРОК 4Б: Роль не студента


@registration_router.callback_query(Registration.non_student_role, F.data.startswith("role_"))
async def process_non_student_role(callback: types.CallbackQuery, state: FSMContext):
    role = callback.data.split("_")[1]
    await state.update_data(non_student_role=role)
    await callback.message.edit_text(f"Твій статус: {role}\n\nОбери свою стать:", reply_markup=gender_kb)
    await state.set_state(Registration.gender)

# КРОК 5: Стать


@registration_router.callback_query(Registration.gender, F.data.startswith("gender_"))
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    gender_name = callback.data.split("_")[1]
    await state.update_data(gender=gender_name)
    await callback.message.edit_text(
        f"Стать: {gender_name}\n\nТепер напиши свою дату народження у форматі DD.MM.YYYY (наприклад, 14.11.2006):"
    )
    await state.set_state(Registration.birth_date)

# КРОК 6: Дата народження


@registration_router.message(Registration.birth_date)
async def process_birth_date(message: types.Message, state: FSMContext):
    try:
        valid_date = datetime.strptime(message.text, "%d.%m.%Y")
        if valid_date.year < 1900 or valid_date.year > 2026:
            await message.answer("Рік виглядає підозріло 👀 Введи реальну дату:")
            return
    except ValueError:
        await message.answer("Ой, формат неправильний. ❌ Напиши дату ось так: 14.11.2006")
        return

    await state.update_data(birth_date=valid_date.date())
    await message.answer("Останній крок! Продовжуючи реєстрацію, nи надаєш згоду на обробку твоїх персональних даних (інститут, вік, стать, час та місце перебування) для внутрішньої статистики заходу. Дані не передаються стороннім особам", reply_markup=consent_kb)
    await state.set_state(Registration.consent)

# КРОК 7: Згода та ЗАПИС У БАЗУ


@registration_router.callback_query(Registration.consent, F.data.startswith("consent_"))
async def process_consent(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    is_consent = True if callback.data.split("_")[1] == "Так" else False

    if not is_consent:
        await callback.message.edit_text("❌ Без згоди на обробку даних ми не можемо тебе зареєструвати.")
        await state.clear()
        return

    data = await state.get_data()

    # Розбиваємо ПІБ на Ім'я та Прізвище для твоєї БД
    name_parts = data['full_name'].split(maxsplit=1)
    last_name = name_parts[0]
    first_name = name_parts[1] if len(name_parts) > 1 else last_name

    # Створюємо юзера в БД через репозиторій
    await create_user(
        session=session,
        telegram_id=data['telegram_id'],
        first_name=first_name,
        last_name=last_name,
        institute=data.get('institute'),
        non_student_type=data.get('non_student_role'),
        student_group=data.get('group'),
        gender=data['gender'],
        birth_date=data['birth_date'],
        username=data.get('telegram_tag'),
        data_consent=is_consent
    )

    await callback.message.edit_text(
        "🎉 Реєстрація успішна! Тепер ти можеш користуватися ботом.",
        reply_markup=get_main_menu_kb("user")
    )
    await state.clear()

# Анти-дурак


@registration_router.message(Registration.institute)
@registration_router.message(Registration.non_student_role)
@registration_router.message(Registration.gender)
@registration_router.message(Registration.consent)
async def ignore_text_input(message: types.Message):
    await message.answer("Будь ласка, скористайся кнопками вище 👆")
