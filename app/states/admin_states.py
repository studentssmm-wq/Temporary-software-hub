from aiogram.fsm.state import State, StatesGroup


class AdminRoleState(StatesGroup):
    waiting_for_admin_id = State()
    waiting_for_volunteer_id = State()


class BroadcastState(StatesGroup):
    waiting_for_message = State()
