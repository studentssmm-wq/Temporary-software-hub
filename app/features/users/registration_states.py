from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    phone_number = State()
    full_name = State()
    institute = State()
    non_student_role = State()
    group = State()
    gender = State()
    birth_date = State()
    consent = State()
