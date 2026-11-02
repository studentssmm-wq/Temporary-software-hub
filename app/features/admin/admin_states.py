from aiogram.fsm.state import State, StatesGroup


class AdminRoleState(StatesGroup):
    waiting_for_admin_id = State()
    waiting_for_volunteer_id = State()


class BroadcastState(StatesGroup):
    waiting_for_type = State()    # Очікуємо вибір: "Зараз" чи "На конкретний час"
    waiting_for_date = State()    # Очікуємо вибір дати (inline-кнопки 1, 2, 3, 4 вересня)
    waiting_for_time = State()    # Очікуємо введення часу вручну (формат ГГ:ХХ)
    waiting_for_filter = State()  # Очікуємо вибір аудиторії (на території / поза / всі)
    waiting_for_message = State() # Очікуємо сам текст або медіа розсилки

class MediaUpdateState(StatesGroup):
    waiting_for_map = State()
    waiting_for_shelter_video = State()
    waiting_for_stretching_video = State()

class ScheduleUpdateState(StatesGroup):
    waiting_for_date = State()
    waiting_for_photos = State()