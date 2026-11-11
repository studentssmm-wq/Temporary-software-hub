from aiogram.fsm.state import State, StatesGroup


class AdminRoleState(StatesGroup):
    waiting_for_admin_id = State()
    waiting_for_volunteer_id = State()


class BroadcastState(StatesGroup):
    waiting_for_type = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_filter = State()
    waiting_for_message = State()

class MediaUpdateState(StatesGroup):
    waiting_for_map = State()
    waiting_for_shelter_video = State()
    waiting_for_stretching_video = State()

class ScheduleUpdateState(StatesGroup):
    waiting_for_date = State()
    waiting_for_photos = State()
