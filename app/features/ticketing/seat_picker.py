"""Telegram seat picker; no external hosting or database writes until checkout."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

PAGE_SIZE = 24

def picker_keyboard(keys, selected, occupied=(), page=0):
    pages = max(1, (len(keys) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    selected, occupied = set(selected), set(occupied)
    buttons = []
    for index in range(page * PAGE_SIZE, min(len(keys), (page + 1) * PAGE_SIZE)):
        key = keys[index]
        mark = '🚫' if key in occupied else '✅' if key in selected else '▫️'
        buttons.append(InlineKeyboardButton(text=f'{mark} {key}', callback_data=f'ticket:pick:toggle:{index}'))
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton(text='◀️', callback_data=f'ticket:pick:page:{max(0,page-1)}'), InlineKeyboardButton(text=f'{page+1}/{pages}', callback_data=f'ticket:pick:page:{page}'), InlineKeyboardButton(text='▶️', callback_data=f'ticket:pick:page:{min(pages-1,page+1)}')])
    rows.append([InlineKeyboardButton(text=f'Підтвердити ({len(selected)})', callback_data='ticket:pick:done')])
    rows.append([InlineKeyboardButton(text='Скасувати', callback_data='ticket:pick:cancel')])
    return InlineKeyboardMarkup(inline_keyboard=rows)

async def start_picker(message, state, keys, *, admin=False, occupied=()):
    from aiogram.types import ReplyKeyboardRemove
    from app.features.ticketing.states import OrderState, AddEventState
    await state.update_data(picker_keys=list(keys), picker_selected=[], picker_page=0, picker_admin=admin)
    await state.set_state(AddEventState.picking_seats if admin else OrderState.choosing_seats)
    await message.answer('Оберіть місця кнопками. Формат: сектор-ряд-місце або ряд-місце. ✅ — обрано, 🚫 — недоступне.', reply_markup=ReplyKeyboardRemove())
    await message.answer('Місця залу:', reply_markup=picker_keyboard(keys, [], occupied))
