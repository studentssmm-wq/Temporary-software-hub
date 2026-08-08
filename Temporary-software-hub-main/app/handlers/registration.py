from datetime import datetime
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from aiogram.types import BufferedInputFile
from app.services.qr_service import create_qr_pass

# Імпортуємо твої клавіатури
from app.keyboards.registration import (
    get_institutes_kb,
    non_student_kb,
    gender_kb,
    consent_kb
)

# Імпортуємо модель User з правильного файлу
from app.database.user import User

router = Router()

# Стейти: прізвище та ім'я розбиті окремо
class Registration(StatesGroup):
    last_name = State()
    first_name = State()
    institute = State()
    non_student_role = State()
    group = State()
    gender = State()
    birth_date = State()
    consent = State()


# КРОК 1: /start -> Питаємо Прізвище
@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.update_data(
        telegram_id=message.from_user.id,
        username=message.from_user.username  # Якщо немає тегу, збережеться None, БД це дозволяє
    )
    await message.answer(
        "Привіт! Починаємо реєстрацію.\nБудь ласка, введи своє **Прізвище**:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(Registration.last_name)


# КРОК 2: Прізвище -> Питаємо Ім'я
@router.message(Registration.last_name)
async def process_last_name(message: types.Message, state: FSMContext):
    await state.update_data(last_name=message.text.strip().capitalize())
    await message.answer("Тепер введи своє **Ім'я**:")
    await state.set_state(Registration.first_name)


# КРОК 3: Ім'я -> Запит Інституту
@router.message(Registration.first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    await state.update_data(first_name=message.text.strip().capitalize())
    await message.answer("Чудово! Обери свій інститут (або вкажи, що ти не студент):", reply_markup=get_institutes_kb())
    await state.set_state(Registration.institute)


# КРОК 4: Інститут (Колбек) -> Група або Хто ти
@router.callback_query(Registration.institute, F.data.startswith("inst_"))
async def process_institute(callback: types.CallbackQuery, state: FSMContext):
    institute_name = callback.data.split("_")[1]

    if institute_name == "Не студент":
        await callback.message.edit_text("Оскільки ти не студент, обери, хто ти:", reply_markup=non_student_kb)
        await state.update_data(institute=None, group=None)
        await state.set_state(Registration.non_student_role)
    else:
        await callback.message.edit_text(f"Обрано інститут: {institute_name}\n\nНапиши свою групу (наприклад, ОІ-12):")
        await state.update_data(institute=institute_name, non_student_role=None)
        await state.set_state(Registration.group)

    await callback.answer()


# КРОК 5А: Група -> Стать
@router.message(Registration.group)
async def process_group(message: types.Message, state: FSMContext):
    await state.update_data(group=message.text.upper().strip())
    await message.answer("Обери свою стать:", reply_markup=gender_kb)
    await state.set_state(Registration.gender)


# КРОК 5Б: Роль не студента -> Стать
@router.callback_query(Registration.non_student_role, F.data.startswith("role_"))
async def process_non_student_role(callback: types.CallbackQuery, state: FSMContext):
    role = callback.data.split("_")[1]
    await state.update_data(non_student_role=role)
    await callback.message.edit_text(f"Твій статус: {role}\n\nОбери свою стать:", reply_markup=gender_kb)
    await state.set_state(Registration.gender)


# КРОК 6: Стать -> Дата народження
@router.callback_query(Registration.gender, F.data.startswith("gender_"))
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    gender_name = callback.data.split("_")[1]
    await state.update_data(gender=gender_name)
    await callback.message.edit_text(
        "Тепер напиши свою дату народження у форматі DD.MM.YYYY (наприклад, 14.11.2006):"
    )
    await state.set_state(Registration.birth_date)


# КРОК 7: Дата народження -> Згода
@router.message(Registration.birth_date)
async def process_birth_date(message: types.Message, state: FSMContext):
    try:
        valid_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        if valid_date.year < 1900 or valid_date.year > 2026:
            await message.answer("Рік виглядає підозріло 👀 Введи реальну дату:")
            return
        await state.update_data(birth_date=valid_date)
    except ValueError:
        await message.answer("Ой, формат неправильний. ❌ Напиши дату ось так: 14.11.2006")
        return

    await message.answer("Останній крок! Чи даєш ти згоду на обробку персональних даних?", reply_markup=consent_kb)
    await state.set_state(Registration.consent)


# КРОК 8: Фінал -> ЗАПИС У БАЗУ
@router.callback_query(Registration.consent, F.data.startswith("consent_"))
async def process_consent(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    consent_answer = callback.data.split("_")[1]
    
    if consent_answer == "Ні":
        await callback.message.edit_text("Без твоєї згоди ми не можемо тебе зареєструвати. 😔 Щоб почати спочатку, пиши /start")
        await state.clear()
        return

    data = await state.get_data()

    try:
        # Створюємо користувача згідно з твоєю моделлю User
        new_user = User(
            telegram_id=data['telegram_id'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            institute=data.get('institute'),
            non_student_type=data.get('non_student_role'),
            student_group=data.get('group'),
            gender=data['gender'],
            birth_date=data['birth_date'],
            username=data.get('username'),
            data_consent=True
        )
        
        session.add(new_user)
        await session.commit()
        
        await callback.message.edit_text("🎉 Реєстрація успішна! Твої дані надійно збережено.")
        
        # === НОВЕ: ОДРАЗУ ВИДАЄМО QR-ПРОПУСК ===
        pass_id, qr_file = await create_qr_pass(session, data['telegram_id'])
        
        photo = BufferedInputFile(
            qr_file.getvalue(),
            filename=f"{pass_id}.png"
        )
        await callback.message.answer_photo(
            photo=photo, 
            caption="Ось твій QR-пропуск для входу! 🎫\n\nТи завжди можеш викликати його знову командою /qr"
        )
        # =======================================
        
    except IntegrityError:
        # Відловлюємо помилку, якщо користувач з таким telegram_id вже є в базі
        await session.rollback()
        await callback.message.edit_text("Ти вже зареєстрований у системі! 😉")
    except Exception as e:
        # Відловлюємо будь-які інші непередбачувані помилки
        await session.rollback()
        print(f"Помилка БД: {e}")
        await callback.message.edit_text("Ой, сталася помилка при збереженні даних. Спробуй пізніше.")

    # Очищуємо стейт
    await state.clear()


# --- АНТИ-ДУРАК ДЛЯ ІНЛАЙН КНОПОК ---
@router.message(Registration.institute)
@router.message(Registration.non_student_role)
@router.message(Registration.gender)
@router.message(Registration.consent)
async def ignore_text_input(message: types.Message):
    await message.answer("Будь ласка, скористайся кнопками вище 👆")