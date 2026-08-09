from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    full_name = State()
    institute = State()
    non_student_role = State()
    group = State()
    gender = State()
    birth_date = State()
    consent = State()
