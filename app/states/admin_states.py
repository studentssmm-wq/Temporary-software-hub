from aiogram.fsm.state import State, StatesGroup


class AdminRoleState(StatesGroup):
    waiting_for_admin_id = State()
    waiting_for_volunteer_id = State()


class BroadcastState(StatesGroup):
    waiting_for_message = State()

class MediaUpdateState(StatesGroup):
    waiting_for_map = State()

class ScheduleUpdateState(StatesGroup):
    waiting_for_date = State()
    waiting_for_photos = State()