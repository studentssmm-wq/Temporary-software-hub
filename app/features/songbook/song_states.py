from aiogram.fsm.state import State, StatesGroup


class SongCreateState(StatesGroup):
    waiting_for_title = State()
    waiting_for_lyrics = State()


class SongEditState(StatesGroup):
    waiting_for_new_title = State()
    waiting_for_new_lyrics = State()
