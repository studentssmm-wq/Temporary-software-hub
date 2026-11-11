import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, WebAppInfo, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.features.ticketing.states import AdminBroadcast, AdminEdit, EditProfile, OrderState, AddEventState, AdminBlacklist, AdminTickets
from app.features.ticketing.runtime import db, bot, ADMIN_IDS, BLACKLIST_CACHE
from app.features.ticketing import sheets
from app.features.ticketing.ticket_generator import create_personalized_ticket
logger = logging.getLogger(__name__)
from app.features.ticketing.keyboards import main_kb, institute_kb, admin_kb, get_organ_hall_kb
from app.features.ticketing.access import TicketAccessFilter, TicketSafetyMiddleware
dp = Router(name='ticket-admin')
dp.callback_query.filter(F.data.startswith('ticket:'))
from app.shared.admin_filter import AdminFilter
dp.message.filter(AdminFilter())
dp.callback_query.filter(AdminFilter())
dp.message.middleware(TicketSafetyMiddleware())
dp.callback_query.middleware(TicketSafetyMiddleware())

@dp.message(F.text == 'Адмін-панель', F.from_user.id.in_(ADMIN_IDS))
async def admin_panel(message: Message):
    await message.answer('Що бажаєте зробити?', reply_markup=admin_kb())

@dp.callback_query(F.data.removeprefix('ticket:') == 'admin_add_event')
async def add_ev_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer('Введіть назву події:')
    await state.set_state(AddEventState.title)

@dp.message(AddEventState.title)
async def add_ev_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer('Прикріпіть афішу до події (надішліть фото):')
    await state.set_state(AddEventState.photo)

@dp.message(AddEventState.photo, F.photo)
async def add_ev_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await message.answer('Введіть опис події:')
    await state.set_state(AddEventState.description)

@dp.message(AddEventState.photo)
async def add_ev_photo_wrong(message: Message):
    await message.answer('❌ Будь ласка, надішліть саме фотографію (афішу):')

@dp.message(AddEventState.description)
async def add_ev_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await message.answer('Введіть дату та час (напр. 20.05 о 18:00):')
    await state.set_state(AddEventState.date_time)

@dp.message(AddEventState.date_time)
async def add_ev_dt(message: Message, state: FSMContext):
    await state.update_data(dt=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🎹 Органний зал', callback_data='ticket:' + 'venue_organ_hall')], [InlineKeyboardButton(text='🏛 Актова зала (NEW)', callback_data='ticket:' + 'venue_assembly_hall')], [InlineKeyboardButton(text='🏢 Інше / Немає значення', callback_data='ticket:' + 'venue_other')]])
    await message.answer('Обери тип локації:', reply_markup=kb)
    await state.set_state(AddEventState.venue_type)

@dp.callback_query(AddEventState.venue_type, F.data.removeprefix('ticket:').startswith('venue_'))
async def add_ev_venue_type(callback: CallbackQuery, state: FSMContext):
    venue_type = callback.data.removeprefix('ticket:').replace('venue_', '')
    if venue_type not in {'organ_hall','assembly_hall','other'}:
        return await callback.answer('Тип зали не підтримується',show_alert=True)
    await state.update_data(venue_type=venue_type)
    if venue_type in {'organ_hall', 'assembly_hall'}:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Усі місця', callback_data='ticket:' + 'seats_all')], [InlineKeyboardButton(text='Обрати конкретні місця', callback_data='ticket:' + 'seats_manual')]])
        await callback.message.edit_text('Як будемо продавати місця у вибраній залі?', reply_markup=kb)
        await state.set_state(AddEventState.seat_selection_mode)
    else:
        await callback.message.edit_text('Тепер введи точне місце проведення текстом:')
        await state.set_state(AddEventState.location)

@dp.callback_query(AddEventState.seat_selection_mode, F.data.removeprefix('ticket:').startswith('seats_'))
async def seat_mode_select(callback: CallbackQuery, state: FSMContext):
    from app.features.ticketing.webapp import venue_url
    from app.features.ticketing.logic import BookingError
    mode = callback.data.removeprefix('ticket:').replace('seats_', '')
    data = await state.get_data()
    if mode == 'all' and data.get('venue_type') in {'organ_hall','assembly_hall'}:
        keys = db.get_full_hall_config(data['venue_type'])
        await state.update_data(selected_seats=keys, total_tickets=len(keys))
        await state.set_state(AddEventState.location)
        return await callback.message.answer('Введіть точну адресу/локацію:')
    from app.features.ticketing.webapp import use_inline_picker
    from app.features.ticketing.seat_picker import start_picker
    try:
        if use_inline_picker():
            raise BookingError('Local picker')
        venue_url(data['venue_type'])
    except BookingError:
        await start_picker(callback.message, state, db.get_full_hall_config(data['venue_type']), admin=True)
        return await callback.answer()
    url = venue_url(data['venue_type'], mode='admin_setup', t=int(time.time()))
    await state.set_state(AddEventState.picking_seats)
    await callback.message.answer('Оберіть усі доступні для продажу місця на схемі.', reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='🗺 Обрати місця', web_app=WebAppInfo(url=url)), KeyboardButton(text='❌ Скасувати')]], resize_keyboard=True))

@dp.callback_query(AddEventState.picking_seats, F.data.removeprefix('ticket:').startswith('seat_toggle:'))
async def toggle_seat(callback: CallbackQuery, state: FSMContext):
    seat_id = callback.data.removeprefix('ticket:').split(':')[1]
    data = await state.get_data()
    selected_seats = data.get('selected_seats', [])
    if seat_id in selected_seats:
        selected_seats.remove(seat_id)
    else:
        selected_seats.append(seat_id)
    await state.update_data(selected_seats=selected_seats)
    await callback.message.edit_reply_markup(reply_markup=get_organ_hall_kb(selected_seats))
    await callback.answer()

@dp.callback_query(AddEventState.picking_seats, F.data.removeprefix('ticket:') == 'seats_done')
async def seats_confirmed(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_seats = data.get('selected_seats', [])
    if not selected_seats:
        return await callback.answer('Оберіть хоча б одне місце!', show_alert=True)
    total_tickets = len(selected_seats)
    await state.update_data(total_tickets=total_tickets)
    await callback.message.answer(f'Обрано місць: {total_tickets}. Введіть точну адресу/локацію:')
    await state.set_state(AddEventState.location)

@dp.message(AddEventState.location)
async def add_ev_location(message: Message, state: FSMContext):
    await state.update_data(location=message.text)
    data = await state.get_data()
    if 'total_tickets' in data:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Так, будуть', callback_data='ticket:' + 'promo_yes')], [InlineKeyboardButton(text='Ні, без промокодів', callback_data='ticket:' + 'promo_no')]])
        await message.answer(f"Кількість квитків визначена автоматично: {data['total_tickets']}\n\nЧи будуть промокоди для цієї події?", reply_markup=kb)
        await state.set_state(AddEventState.ask_promo)
    else:
        await message.answer('Введіть загальну кількість квитків на подію (тільки число):')
        await state.set_state(AddEventState.total_tickets)

@dp.message(AddEventState.total_tickets)
async def add_ev_tickets(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        return await message.answer('Введіть ціле додатнє число (більше нуля)!')
    await state.update_data(total_tickets=int(message.text))
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Так, будуть', callback_data='ticket:' + 'promo_yes')], [InlineKeyboardButton(text='Ні, без промокодів', callback_data='ticket:' + 'promo_no')]])
    await message.answer('Чи будуть промокоди для цієї події?', reply_markup=kb)
    await state.set_state(AddEventState.ask_promo)

@dp.callback_query(AddEventState.ask_promo, F.data.removeprefix('ticket:').in_(['promo_yes', 'promo_no']))
async def ask_promo_step(callback: CallbackQuery, state: FSMContext):
    if callback.data.removeprefix('ticket:') == 'promo_yes':
        await state.update_data(has_promo=True, promo_list=[])
        await callback.message.edit_text('Вводь промокоди ПО ОДНОМУ. Коли додаси всі, напиши слово <b>СТОП</b>:', parse_mode='HTML')
        await state.set_state(AddEventState.wait_promo_list)
    else:
        await state.update_data(has_promo=False, promo_list=[], promo_discount=0)
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Безкоштовна', callback_data='ticket:' + 'ev_free')], [InlineKeyboardButton(text='Платна', callback_data='ticket:' + 'ev_paid')]])
        await callback.message.edit_text('Яка це подія?', reply_markup=kb)
        await state.set_state(AddEventState.is_free)

@dp.message(AddEventState.wait_promo_list)
async def collect_promocodes(message: Message, state: FSMContext):
    if message.text.strip().upper() == 'СТОП':
        await message.answer('Супер! Тепер введи <b>знижку на 1 квиток</b> у гривнях (тільки число, напр. 50):', parse_mode='HTML')
        await state.set_state(AddEventState.wait_promo_discount)
    else:
        data = await state.get_data()
        promo_list = data.get('promo_list', [])
        promo_list.append(message.text.strip().upper())
        await state.update_data(promo_list=promo_list)
        await message.answer(f"✅ Промокод '<b>{message.text.strip().upper()}</b>' додано. Вводь наступний або пиши СТОП.", parse_mode='HTML')

@dp.message(AddEventState.wait_promo_discount)
async def get_promo_discount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer('Тільки число!')
    await state.update_data(promo_discount=int(message.text))
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Безкоштовна', callback_data='ticket:' + 'ev_free')], [InlineKeyboardButton(text='Платна', callback_data='ticket:' + 'ev_paid')]])
    await message.answer('Яка це подія?', reply_markup=kb)
    await state.set_state(AddEventState.is_free)

@dp.callback_query(AddEventState.is_free, F.data.removeprefix('ticket:').in_(['ev_free', 'ev_paid']))
async def set_ev_type(callback: CallbackQuery, state: FSMContext):
    is_free = callback.data.removeprefix('ticket:') == 'ev_free'
    await state.update_data(is_free=is_free)
    if is_free:
        await state.update_data(is_fixed_price=True, price='0', link='', card='', requires_confirmation=False)
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='📷 З фото-квитком (QR)', callback_data='ticket:' + 'qr_yes')], [InlineKeyboardButton(text='📝 Звичайний (текст / стандарт)', callback_data='ticket:' + 'qr_no')]])
        await callback.message.edit_text('Чи потрібно генерувати графічний квиток з QR-кодом?', reply_markup=kb)
        await state.set_state(AddEventState.ask_qr)
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Фіксована ціна', callback_data='ticket:' + 'price_fixed')], [InlineKeyboardButton(text='Гнучка ціна (текст)', callback_data='ticket:' + 'price_flex')]])
        await callback.message.edit_text('Який формат ціни буде у події?', reply_markup=kb)
        await state.set_state(AddEventState.price_type)
    await callback.answer()

@dp.callback_query(AddEventState.price_type, F.data.removeprefix('ticket:').in_(['price_fixed', 'price_flex']))
async def set_price_type(callback: CallbackQuery, state: FSMContext):
    is_fixed = callback.data.removeprefix('ticket:') == 'price_fixed'
    await state.update_data(is_fixed_price=is_fixed)
    if is_fixed:
        await callback.message.edit_text('Введіть ціну за 1 квиток (ТІЛЬКИ ЧИСЛО, напр. 150):')
    else:
        await callback.message.edit_text("Введіть текст ціни (напр. 'від 100 грн' або 'донат від 50 грн'):")
    await state.set_state(AddEventState.price)
    await callback.answer()

@dp.message(AddEventState.price)
async def add_ev_price(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get('is_fixed_price') and (not message.text.isdigit()):
        return await message.answer('Помилка! Для фіксованої ціни введіть ТІЛЬКИ ЧИСЛО:')
    await state.update_data(price=message.text)
    await message.answer('Введіть посилання на банку Monobank:')
    await state.set_state(AddEventState.bank_link)

@dp.message(AddEventState.bank_link)
async def add_ev_link(message: Message, state: FSMContext):
    await state.update_data(link=message.text)
    await message.answer('Введіть номер картки (тільки цифри):')
    await state.set_state(AddEventState.card_number)

@dp.message(AddEventState.card_number)
async def add_ev_card(message: Message, state: FSMContext):
    await state.update_data(card=message.text)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='📷 З фото-квитком (QR)', callback_data='ticket:' + 'qr_yes')], [InlineKeyboardButton(text='📝 Звичайний (текст / стандарт)', callback_data='ticket:' + 'qr_no')]])
    await message.answer('Чи потрібно генерувати графічний квиток з QR-кодом?', reply_markup=kb)
    await state.set_state(AddEventState.ask_qr)

@dp.callback_query(AddEventState.ask_qr, F.data.removeprefix('ticket:').in_(['qr_yes', 'qr_no']))
async def set_ev_qr_option(callback: CallbackQuery, state: FSMContext):
    generates_qr = callback.data.removeprefix('ticket:') == 'qr_yes'
    await state.update_data(generates_qr_ticket=generates_qr)
    await callback.message.edit_text('Введіть фінальне повідомлення після підтвердження замовлення/оплати:')
    await state.set_state(AddEventState.success_message)
    await callback.answer()

@dp.message(AddEventState.success_message)
async def add_ev_final(message: Message, state: FSMContext):
    d = await state.get_data()
    seats_data = d.get('selected_seats')
    available_seats_str = None
    if isinstance(seats_data, list):
        available_seats_str = ','.join(seats_data)
    elif seats_data == 'all':
        available_seats_str = None
    has_promo = d.get('has_promo', False)
    promo_list_str = ','.join(d.get('promo_list', [])) if has_promo and d.get('promo_list') else None
    promo_disc = d.get('promo_discount', 0)
    generates_qr = d.get('generates_qr_ticket', False)
    await db.add_event(d['title'], d['desc'], d['photo_id'], d['dt'], d['venue_type'], d['location'], d['total_tickets'], d['is_free'], d['price'], d.get('link', ''), d.get('card', ''), message.text, available_seats_str, has_promo, promo_list_str, promo_disc, generates_qr)
    await message.answer('✅ Подію успішно додано!', reply_markup=main_kb(message.from_user.id))
    await state.clear()

@dp.callback_query(F.data.removeprefix('ticket:') == 'admin_del_list')
async def show_delete_list(callback: CallbackQuery):
    events = await db.get_active_events()
    if not events:
        return await callback.message.answer('Немає активних подій для видалення.')
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{ev['title']}", callback_data='ticket:' + f"del_{ev['id']}")] for ev in events])
    await callback.message.answer('Оберіть подію, яку хочете ВИДАЛИТИ:', reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.removeprefix('ticket:').startswith('del_'))
async def confirm_delete(callback: CallbackQuery):
    event_id = int(callback.data.removeprefix('ticket:').split('_')[1])
    await db.delete_event(event_id)
    await callback.message.edit_text('Подію успішно видалено! (Вона більше не показуватиметься студентам).')

@dp.callback_query(F.data.removeprefix('ticket:') == 'admin_edit_list')
async def show_edit_list(callback: CallbackQuery, state: FSMContext):
    events = await db.get_active_events()
    if not events:
        return await callback.message.answer('Немає активних подій для редагування.')
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{ev['title']}", callback_data='ticket:' + f"edit_{ev['id']}")] for ev in events])
    await callback.message.answer('Оберіть подію для РЕДАГУВАННЯ:', reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.removeprefix('ticket:').startswith('edit_'))
async def select_field_to_edit(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.removeprefix('ticket:').split('_')[1])
    await state.update_data(edit_ev_id=event_id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Назву', callback_data='ticket:' + 'field_title'), InlineKeyboardButton(text='Опис', callback_data='ticket:' + 'field_description')], [InlineKeyboardButton(text='Фото афіші', callback_data='ticket:' + 'field_photo_id'), InlineKeyboardButton(text='Локацію', callback_data='ticket:' + 'field_location')], [InlineKeyboardButton(text='Дату/Час', callback_data='ticket:' + 'field_date_time'), InlineKeyboardButton(text='Ціну', callback_data='ticket:' + 'field_price')], [InlineKeyboardButton(text='К-сть квитків', callback_data='ticket:' + 'field_total_tickets'), InlineKeyboardButton(text='Повідомлення', callback_data='ticket:' + 'field_success_message')]])
    await callback.message.edit_text('Що саме ви хочете змінити?', reply_markup=kb)
    await state.set_state(AdminEdit.select_field)

@dp.callback_query(AdminEdit.select_field, F.data.removeprefix('ticket:').startswith('field_'))
async def enter_new_value(callback: CallbackQuery, state: FSMContext):
    field_name = callback.data.removeprefix('ticket:').replace('field_', '')
    data = await state.get_data()
    event = await db.get_event(data['edit_ev_id'])
    if field_name == 'price' and event['is_free']:
        return await callback.answer('❌ Це безкоштовна подія! Ціну змінити неможливо.', show_alert=True)
    await state.update_data(edit_field=field_name)
    names_ua = {'title': 'нову НАЗВУ', 'description': 'новий ОПИС', 'photo_id': 'нову АФІШУ (надішліть фото)', 'date_time': 'нову ДАТУ та ЧАС', 'location': 'нову ЛОКАЦІЮ', 'total_tickets': 'нову загальну КІЛЬКІСТЬ КВИТКІВ (число)', 'price': 'нову ЦІНУ', 'success_message': 'нове ФІНАЛЬНЕ ПОВІДОМЛЕННЯ'}
    await callback.message.edit_text(f"Введіть {names_ua.get(field_name, 'нове значення')}:")
    await state.set_state(AdminEdit.enter_value)

@dp.message(AdminEdit.enter_value)
async def save_new_value(message: Message, state: FSMContext):
    data = await state.get_data()
    field_name = data['edit_field']
    if field_name == 'photo_id':
        if not message.photo:
            return await message.answer('❌ Будь ласка, надішліть нове фото афіші:')
        new_value = message.photo[-1].file_id
    else:
        new_value = message.text
    event = await db.get_event(data['edit_ev_id'])
    if field_name == 'total_tickets' and (not new_value.isdigit() or int(new_value) <= 0):
        return await message.answer('❌ Помилка! Введіть додатнє число більше нуля:')
    if field_name == 'price' and event.get('is_fixed_price') and (not new_value.isdigit() or int(new_value) < 0):
        return await message.answer('❌ Помилка! Для фіксованої ціни введіть тільки число:')
    await db.update_event_field(data['edit_ev_id'], field_name, int(new_value) if field_name == 'total_tickets' else new_value)
    await message.answer('✅ Зміни успішно збережено!')
    await state.clear()

@dp.callback_query(F.data.removeprefix('ticket:') == 'admin_upload_tickets')
async def admin_upload_tickets_start(callback: CallbackQuery, state: FSMContext):
    events = await db.get_active_events()
    organ_events = [ev for ev in events if ev.get('venue_type') == 'organ_hall']
    if not organ_events:
        return await callback.message.answer('Немає активних подій в Органному залі.')
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{ev['title']}", callback_data='ticket:' + f"up_tkt_{ev['id']}")] for ev in organ_events])
    await callback.message.edit_text("Обери подію, до якої хочеш прив'язати квитки:", reply_markup=kb)

@dp.callback_query(F.data.removeprefix('ticket:').startswith('up_tkt_'))
async def admin_ready_to_upload(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.removeprefix('ticket:').split('_')[2])
    await state.update_data(upload_event_id=event_id)
    await callback.message.edit_text("📤 <b>Режим завантаження квитків увімкнено!</b>\n\nНадсилай сюди фото або ПДФ файли квитків.\n❗️ <b>ОБОВ'ЯЗКОВО</b> в підписі до кожного файлу пиши ряд і місце через пробіл (напр: <code>1 12</code> або <code>12Б 5</code>).\n\n<i>Можеш виділити кілька файлів одразу, головне кожному додати підпис.</i>\n\nКоли закінчиш, натисни кнопку нижче.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='✅ Завершити завантаження', callback_data='ticket:' + 'finish_upload')]]), parse_mode='HTML')
    await state.set_state(AdminTickets.uploading)

@dp.message(AdminTickets.uploading, F.photo | F.document)
async def process_ticket_file(message: Message, state: FSMContext):
    caption = message.caption
    if not caption:
        return await message.answer('❌ Файл проігноровано: ти забув додати підпис (ряд і місце)!')
    parts = caption.strip().split()
    if len(parts) != 2:
        return await message.answer(f"❌ Файл проігноровано: неправильний формат підпису '{caption}'. Треба 'Ряд Місце' (напр. '1 12').")
    row, seat = (parts[0], parts[1])
    data = await state.get_data()
    event_id = data['upload_event_id']
    f_id = message.photo[-1].file_id if message.photo else message.document.file_id
    f_type = 'photo' if message.photo else 'document'
    await db.add_seat_ticket(event_id, row, seat, f_id, f_type)
    await message.answer(f'✅ Збережено квиток для: Ряд {row}, Місце {seat}')

@dp.callback_query(AdminTickets.uploading, F.data.removeprefix('ticket:') == 'finish_upload')
async def finish_ticket_upload(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text('✅ Завантаження квитків завершено! Вони автоматично надсилатимуться покупцям.')
    await state.clear()

@dp.callback_query(F.data.removeprefix('ticket:') == 'admin_mass_upload')
async def admin_mass_upload_start(callback: CallbackQuery, state: FSMContext):
    events = await db.get_active_events()
    organ_events = [ev for ev in events if ev.get('venue_type') == 'organ_hall']
    if not organ_events:
        return await callback.message.answer('Немає активних подій в Органному залі.')
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{ev['title']}", callback_data='ticket:' + f"mass_tkt_{ev['id']}")] for ev in organ_events])
    await callback.message.edit_text('Обери подію для МАСОВОГО завантаження квитків:', reply_markup=kb)

@dp.callback_query(F.data.removeprefix('ticket:').startswith('mass_tkt_'))
async def admin_ready_to_mass_upload(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.removeprefix('ticket:').split('_')[2])
    await state.update_data(upload_event_id=event_id, uploaded_count=0)
    await callback.message.edit_text("📂 <b>МАСОВЕ ЗАВАНТАЖЕННЯ УВІМКНЕНО!</b>\n\nПросто виділи всі PDF-файли квитків (можна до 100 шт. за раз) і відправ їх мені.\n\n⚠️ <b>ВАЖЛИВО:</b> Назви файлів повинні містити ряд і місце після слова 'Партер', наприклад:\n<code>10895874_Партер_24_1_2025-10-04_1.pdf</code>\n\n<i>Я сам прочитаю назву і розкладу їх по місцях. Ніяких підписів додавати не треба!</i>\n\nКоли завантажиш усі файли, натисни кнопку нижче.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='✅ Завершити масове завантаження', callback_data='ticket:' + 'finish_mass_upload')]]), parse_mode='HTML')
    await state.set_state(AdminTickets.mass_uploading)

@dp.message(AdminTickets.mass_uploading, F.document)
async def process_mass_ticket_file(message: Message, state: FSMContext):
    file_name = message.document.file_name
    match = re.search('^[^_]+_[^_]+_([0-9А-Яа-я]+)_(\\d+)_', file_name, re.IGNORECASE)
    if not match:
        return await message.answer(f"❌ Файл <b>{file_name}</b> проігноровано: назва не відповідає формату 'Номер_Сектор_РЯД_МІСЦЕ_Дата'.", parse_mode='HTML')
    row = match.group(1)
    seat = match.group(2)
    data = await state.get_data()
    event_id = data['upload_event_id']
    f_id = message.document.file_id
    await db.add_seat_ticket(event_id, row, seat, f_id, 'document')
    new_count = data.get('uploaded_count', 0) + 1
    await state.update_data(uploaded_count=new_count)
    if new_count <= 3 or new_count % 10 == 0:
        await message.answer(f'✅ Збережено: Ряд {row}, Місце {seat} <i>({file_name})</i>. Всього: {new_count}', parse_mode='HTML')

@dp.callback_query(AdminTickets.mass_uploading, F.data.removeprefix('ticket:') == 'finish_mass_upload')
async def finish_mass_upload(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    count = data.get('uploaded_count', 0)
    await callback.message.edit_text(f'✅ <b>Масове завантаження завершено!</b>\nУспішно збережено квитків: <b>{count}</b> шт.', parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data.removeprefix('ticket:').startswith('conf_') | F.data.removeprefix('ticket:').startswith('reje_'))
async def handle_decision(callback: CallbackQuery):
    from app.features.ticketing.delivery import deliver_order
    action, order_str = callback.data.removeprefix('ticket:').split('_', 1)
    order_id = int(order_str)
    order = await db.get_order(order_id)
    if not order or order['status'] not in {'pending', 'pending_manual'}:
        return await callback.answer('Це замовлення вже опрацьоване', show_alert=True)
    status = 'confirmed' if action == 'conf' else 'rejected'
    changed = await db.update_order_status(order_id, status)
    await callback.answer('Рішення збережено')
    await callback.message.edit_reply_markup(reply_markup=None)
    if changed:
        event = await db.get_event(order['event_id'])
        await sheets.update_payment_in_sheet(event['title'], order_id, status, event['venue_type'])
        if status == 'confirmed':
            await deliver_order(order_id, bot)
        else:
            await bot.send_message(order['user_id'], f'Оплату NULP-{order_id} відхилено. Зверніться до підтримки.')

@dp.callback_query(F.data.removeprefix('ticket:') == 'admin_broadcast')
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    from app.core.config import ENABLE_MAILINGS
    if not ENABLE_MAILINGS:
        return await callback.answer('Розсилки вимкнено у цьому середовищі')
    events = await db.get_active_events()
    kb_buttons = [[InlineKeyboardButton(text='📢 Усім зареєстрованим у боті', callback_data='ticket:' + 'bcast_all')]]
    for ev in events:
        kb_buttons.append([InlineKeyboardButton(text=f"🎫 Тільки: {ev['title']}", callback_data='ticket:' + f"bcast_ev_{ev['id']}")])
    kb_buttons.append([InlineKeyboardButton(text='❌ Скасувати', callback_data='ticket:' + 'bcast_cancel')])
    await callback.message.edit_text('<b>Кому хочеш надіслати повідомлення?</b>', reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons), parse_mode='HTML')
    await state.set_state(AdminBroadcast.choose_audience)

@dp.callback_query(AdminBroadcast.choose_audience, F.data.removeprefix('ticket:').startswith('bcast_'))
async def choose_broadcast_audience(callback: CallbackQuery, state: FSMContext):
    action = callback.data.removeprefix('ticket:').replace('bcast_', '')
    if action == 'cancel':
        await callback.message.edit_text('❌ Розсилку скасовано.')
        return await state.clear()
    await state.update_data(broadcast_target=action)
    await callback.message.edit_text("📢 <b>Режим розсилки</b>\nНадішли мені повідомлення.\n<i>Щоб скасувати, напиши 'Скасувати'.</i>", parse_mode='HTML')
    await state.set_state(AdminBroadcast.waiting_for_message)

@dp.message(AdminBroadcast.waiting_for_message)
async def process_broadcast(message: Message, state: FSMContext):
    from app.core.config import ENABLE_MAILINGS
    if not ENABLE_MAILINGS:
        return await message.answer('Розсилки вимкнено у цьому середовищі')
    if message.text and message.text.lower() == 'скасувати':
        await message.answer('❌ Розсилку скасовано.')
        return await state.clear()
    data = await state.get_data()
    target = data.get('broadcast_target')
    users = await db.get_all_users() if target == 'all' else await db.get_users_by_event(int(target.replace('ev_', '')))
    if not users:
        await message.answer('🤷\u200d♂️ Не знайдено користувачів для цієї розсилки.')
        return await state.clear()
    await message.answer(f'🚀 Починаю розсилку для {len(users)} користувачів...')
    success, blocked = (0, 0)
    for user in users:
        try:
            await message.copy_to(user['tg_id'])
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            blocked += 1
    await message.answer(f'✅ <b>Розсилку завершено!</b>\n\n📨 Успішно: {success}\n🚫 Заблокували: {blocked}', parse_mode='HTML')
    await state.clear()

@dp.callback_query(F.data.removeprefix('ticket:') == 'admin_blacklist')
async def admin_bl_menu(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Додати юзера', callback_data='ticket:' + 'bl_add')], [InlineKeyboardButton(text='Видалити юзера', callback_data='ticket:' + 'bl_remove')], [InlineKeyboardButton(text='Список', callback_data='ticket:' + 'bl_list')]])
    await callback.message.edit_text('⚫ <b>Керування чорним списком</b>', reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.removeprefix('ticket:') == 'bl_add')
async def bl_add(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text('Введіть @юзернейм людини, яку треба забанити:')
    await state.set_state(AdminBlacklist.add)

@dp.message(AdminBlacklist.add)
async def process_bl_add(message: Message, state: FSMContext):
    await db.add_to_blacklist(message.text)
    BLACKLIST_CACHE.add(message.text.replace('@', '').strip().lower())
    await message.answer(f'✅ Користувача {message.text} додано до чорного списку.', reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(F.data.removeprefix('ticket:') == 'bl_remove')
async def bl_remove(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text('Введіть @юзернейм людини для розблокування:')
    await state.set_state(AdminBlacklist.remove)

@dp.message(AdminBlacklist.remove)
async def process_bl_remove(message: Message, state: FSMContext):
    await db.remove_from_blacklist(message.text)
    BLACKLIST_CACHE.discard(message.text.replace('@', '').strip().lower())
    await message.answer(f'✅ Користувача {message.text} розблоковано.', reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(F.data.removeprefix('ticket:') == 'bl_list')
async def bl_list(callback: CallbackQuery):
    banned = await db.get_blacklist()
    if not banned:
        await callback.message.edit_text('Чорний список пустий.', reply_markup=admin_kb())
    else:
        text = '⚫ <b>Заблоковані юзери:</b>\n' + '\n'.join([f'- @{u}' for u in banned])
        await callback.message.edit_text(text, reply_markup=admin_kb(), parse_mode='HTML')

@dp.callback_query(F.data.removeprefix('ticket:') == 'admin_manage_hall')
async def admin_manage_hall_list(callback: CallbackQuery):
    events = await db.get_active_events()
    hall_events = [ev for ev in events if ev.get('venue_type') in ['organ_hall', 'assembly_hall']]
    if not hall_events:
        return await callback.message.answer('🤷\u200d♂️ Наразі немає активних подій з картою залу.')
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"🗺 {ev['title']}", callback_data='ticket:' + f"adm_hall_{ev['id']}")] for ev in hall_events])
    await callback.message.edit_text('<b>Оберіть подію для керуванням розсадкою:</b>', reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.removeprefix('ticket:').startswith('adm_hall_'))
async def open_admin_hall(callback: CallbackQuery, state: FSMContext):
    from app.features.ticketing.webapp import venue_url
    event_id=int(callback.data.removeprefix('ticket:').split('_')[2])
    event=await db.get_event(event_id)
    if not event:
        return await callback.answer('Подія недоступна',show_alert=True)
    from app.features.ticketing.webapp import use_inline_picker
    from app.features.ticketing.logic import BookingError
    try:
        if use_inline_picker():
            raise BookingError('Local picker')
        venue_url(event['venue_type'])
    except BookingError:
        await state.clear()
        await state.update_data(inspect_event_id=event_id)
        await callback.answer()
        return await show_local_hall(callback.message, state, event_id)
    url=venue_url(event['venue_type'],occ=','.join(await db.get_occupied_seats(event_id)),admin='true',ev_id=event_id,t=int(time.time()))
    kb=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='🛠 Відкрити карту',web_app=WebAppInfo(url=url))]],resize_keyboard=True,one_time_keyboard=True)
    await callback.answer()
    await callback.message.answer('Відкрийте карту для перегляду зайнятих місць.',reply_markup=kb)

@dp.callback_query(F.data.removeprefix('ticket:').startswith('adm_cancel_'))
async def perform_adm_cancel(callback: CallbackQuery):
    parts = callback.data.removeprefix('ticket:').split('_')
    order_id, row, seat = (int(parts[2]), parts[3], parts[4])
    order = await db.get_order(order_id)
    if not order:
        return await callback.answer('Замовлення не знайдено', show_alert=True)
    event = await db.get_event(order['event_id'])
    success = await db.remove_seat_from_order(order_id, row, seat)
    if success:
        await sheets.cancel_seat_in_sheet(event['title'], order_id, row, seat, event['venue_type'])
        await callback.message.edit_text(callback.message.text + f'\n\n❌ <b>Квиток (Ряд {row}, Місце {seat}) скасовано в БД та Таблиці!</b>', parse_mode='HTML')
        try:
            await bot.send_message(order['user_id'], f"⚠️ <b>Твій квиток скасовано</b>\nАдміністрація скасувала твоє місце (Ряд {row}, Місце {seat}) на подію <b>{event['title']}</b>.\nЩодо повернення коштів зверніться до організаторів.", parse_mode='HTML')
        except:
            pass
    else:
        await callback.answer('Помилка при видаленні', show_alert=True)


@dp.callback_query(F.data == "ticket:admin_home")
async def ticket_admin_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.answer("Керування квитками та подіями",reply_markup=admin_kb())

async def show_local_hall(message: Message, state: FSMContext, event_id, page=0):
    keys = db.get_full_hall_config((await db.get_event(event_id))['venue_type'])
    occupied = set(await db.get_occupied_seats(event_id))
    rows = []
    for index in range(page*24, min(len(keys), (page+1)*24)):
        key = keys[index]
        button = InlineKeyboardButton(text=('🔴 ' if key in occupied else '▫️ ')+key, callback_data=f'ticket:inspect:{index}')
        if (index-page*24)%3 == 0:
            rows.append([])
        rows[-1].append(button)
    last = max(0,(len(keys)-1)//24)
    rows.append([InlineKeyboardButton(text='◀️',callback_data=f'ticket:inspectpage:{max(0,page-1)}'),InlineKeyboardButton(text=f'{page+1}/{last+1}',callback_data=f'ticket:inspectpage:{min(last,page+1)}')])
    await message.answer('Місця залу: 🔴 зайняте або закрите для продажу. Натисніть для перегляду замовлення.',reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))

@dp.callback_query(F.data.startswith('ticket:inspectpage:'))
async def local_hall_page(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get('inspect_event_id'):
        return await callback.answer('Відкрийте зал знову',show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=None)
    await show_local_hall(callback.message,state,data['inspect_event_id'],max(0,int(callback.data.rsplit(':',1)[1])))
    await callback.answer()

@dp.callback_query(F.data.startswith('ticket:inspect:'))
async def local_hall_details(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    event_id = data.get('inspect_event_id')
    event = await db.get_event(event_id) if event_id else None
    if not event:
        return await callback.answer('Відкрийте зал знову',show_alert=True)
    keys = db.get_full_hall_config(event['venue_type'])
    index = int(callback.data.rsplit(':',1)[1])
    if not 0 <= index < len(keys):
        return await callback.answer('Недійсне місце',show_alert=True)
    row, seat = keys[index].rsplit('-',1)
    info = await db.get_seat_info(event_id,row,seat)
    if not info:
        return await callback.answer('Замовлення на це місце відсутнє',show_alert=True)
    await callback.message.answer(f"Місце: {keys[index]}. Замовлення NULP-{info['order_id']}. Покупець: {info['first_name']} {info['last_name']}",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Скасувати квиток',callback_data=f"ticket:adm_cancel_{info['order_id']}_{row}_{seat}")]]))
    await callback.answer()
