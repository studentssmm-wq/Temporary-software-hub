from app.features.users.registration_keyboard import NULP_INSTITUTES
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
from app.features.ticketing.runtime import db, bot, ADMIN_IDS, BLACKLIST_CACHE, get_admin_ids
from app.features.ticketing import sheets
from app.features.ticketing.ticket_generator import create_personalized_ticket
logger = logging.getLogger(__name__)
from app.features.ticketing.keyboards import main_kb, institute_kb, admin_kb, get_organ_hall_kb
from app.features.ticketing.access import TicketAccessFilter, TicketSafetyMiddleware
dp = Router(name='ticket-purchase')
dp.callback_query.filter(F.data.startswith('ticket:'))
dp.message.filter(TicketAccessFilter())
dp.callback_query.filter(TicketAccessFilter())
dp.message.middleware(TicketSafetyMiddleware())
dp.callback_query.middleware(TicketSafetyMiddleware())


async def admin_panel(message: Message):
    if message.from_user.id not in await get_admin_ids():
        return await message.answer('Доступ лише для адміністраторів.')
    from app.features.ticketing.admin import admin_panel as show_admin_panel
    await show_admin_panel(message)

def extract_min_price(price_str):
    """Витягує перше число з рядка. Якщо там просто '150', поверне 150."""
    price_str = str(price_str).strip()
    if price_str.isdigit():
        return int(price_str)
    match = re.search('\\d+', price_str)
    return int(match.group()) if match else 0

@dp.message(F.text == 'Мій профіль')
async def show_profile(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_user(message.from_user.id)
    if not user:
        return await message.answer('❌ Профіль не знайдено. Напиши /start')
    if user['institute'] == 'Я не студент':
        inst_label = '👤 <b>Статус:</b>'
        group_label = '📝 <b>Діяльність:</b>'
    elif user['institute'] in NULP_INSTITUTES:
        inst_label = '🏛 <b>Інститут (ЛП):</b>'
        group_label = '🎓 <b>Група:</b>'
    else:
        inst_label = '🏛 <b>Університет:</b>'
        group_label = '🎓 <b>Група/Факультет:</b>'
    profile_text = f"👤 <b>ТВІЙ ПРОФІЛЬ</b>\n\n📝 <b>Прізвище:</b> {user['last_name']}\n📝 <b>Ім'я:</b> {user['first_name']}\n{inst_label} {user['institute']}\n{group_label} {user['student_group']}\n\n<i>Тисни на кнопки нижче, якщо треба щось змінити 👇</i>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='✏️ Прізвище', callback_data='ticket:' + 'prof_edit_last_name'), InlineKeyboardButton(text="✏️ Ім'я", callback_data='ticket:' + 'prof_edit_first_name')], [InlineKeyboardButton(text='✏️ Інститут / Статус', callback_data='ticket:' + 'prof_edit_institute')], [InlineKeyboardButton(text='✏️ Групу / Примітку', callback_data='ticket:' + 'prof_edit_group')]])
    await message.answer(profile_text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.removeprefix('ticket:').startswith('prof_edit_'))
async def ask_new_profile_value(callback: CallbackQuery, state: FSMContext):
    field_to_edit = callback.data.removeprefix('ticket:').replace('prof_edit_', '')
    await state.update_data(edit_field=field_to_edit)
    user = await db.get_user(callback.from_user.id)
    is_nulp = user['institute'] in NULP_INSTITUTES
    if field_to_edit == 'last_name':
        text = '✍️ Введи своє нове <b>Прізвище</b>:'
    elif field_to_edit == 'first_name':
        text = "✍️ Введи своє нове <b>Ім'я</b>:"
    elif field_to_edit == 'institute':
        text = '🏛 Обери свій <b>Інститут</b> або статус:'
        await callback.message.answer(text, reply_markup=institute_kb(), parse_mode='HTML')
        await state.set_state(EditProfile.enter_value)
        return await callback.answer()
    elif field_to_edit == 'group':
        if is_nulp:
            text = '🎓 Введи свою нову <b>Групу</b>:'
        elif user['institute'] == 'Я не студент':
            text = '📝 Вкажи свою <b>діяльність</b> (напр. Гість):'
        else:
            text = '🎓 Вкажи свою <b>Групу або Факультет</b> у твоєму ВНЗ:'
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(text, parse_mode='HTML')
    await state.set_state(EditProfile.enter_value)
    await callback.answer()

@dp.message(EditProfile.enter_value)
async def save_new_profile_value(message: Message, state: FSMContext):
    if message.text in ['Доступні події', 'Мій профіль', 'Адмін-панель']:
        await state.clear()
        if message.text == 'Доступні події':
            return await list_events(message)
        elif message.text == 'Мій профіль':
            return await show_profile(message, state)
        else:
            return await admin_panel(message)
    data = await state.get_data()
    field = data['edit_field']
    new_val = message.text
    await db.update_user_field(message.from_user.id, field, new_val)
    user = await db.get_user(message.from_user.id)
    if user:
        asyncio.create_task(sheets.upsert_user_in_registry(user['last_name'], user['first_name'], user['username'], user['institute'], user['student_group']))
    await message.answer('✅ <b>Готово! Я все оновив.</b>', reply_markup=ReplyKeyboardRemove() if field == 'institute' else None, parse_mode='HTML')
    await state.clear()
    await show_profile(message, state)

@dp.message(F.text == 'Доступні події')
async def list_events(message: Message):
    events = await db.get_active_events()
    if not events:
        return await message.answer('📭 <b>Наразі активних подій немає.</b>', parse_mode='HTML')
    for ev in events:
        rem = ev['remaining_tickets']
        if rem <= 0:
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ Квитків немає', callback_data='ticket:' + 'sold_out')]])
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🎟 Купити квиток', callback_data='ticket:' + f"buy_{ev['id']}")]])
        type_str = '<i>Безкоштовно</i>' if ev['is_free'] else f"<b>{ev['price']}</b>"
        event_text = f"🎉 <b>{ev['title']}</b>\n\n📅 <b>Коли:</b> {ev['date_time']}\n📍 <b>Локація:</b> {ev['location']}\n💵 <b>Вартість:</b> {type_str}\n\n<i>{ev['description']}</i>"
        if ev.get('photo_id'):
            await message.answer_photo(ev['photo_id'], caption=event_text, reply_markup=kb, parse_mode='HTML')
        else:
            await message.answer(event_text, reply_markup=kb, parse_mode='HTML')

@dp.callback_query(F.data.removeprefix('ticket:') == 'sold_out')
async def handle_sold_out(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer('🥺 На жаль, усі квитки на цю подію вже розібрали!', parse_mode='HTML')
    await callback.answer()

async def proceed_to_buy_logic(message: Message, state: FSMContext, event: dict):
    from app.features.ticketing.webapp import venue_url
    if event.get('venue_type') in ['organ_hall', 'assembly_hall']:
        from app.features.ticketing.webapp import use_inline_picker
        from app.features.ticketing.seat_picker import start_picker
        from app.features.ticketing.logic import BookingError
        occupied = await db.get_occupied_seats(event['id'])
        try:
            if use_inline_picker():
                raise BookingError('Local picker')
            venue_url(event['venue_type'])
        except BookingError:
            return await start_picker(message, state, db.get_full_hall_config(event['venue_type']), occupied=occupied)
        url = venue_url(event['venue_type'], occ=','.join(await db.get_occupied_seats(event['id'])), ev_id=event['id'], t=int(time.time()))
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='🗺 Відкрити схему залу', web_app=WebAppInfo(url=url)), KeyboardButton(text='❌ Скасувати')]], resize_keyboard=True)
        await state.set_state(OrderState.waiting_for_quantity)
        await message.answer('Оберіть місця на схемі залу.', reply_markup=kb)
    else:
        await state.set_state(OrderState.waiting_for_quantity)
        await message.answer('Скільки квитків беремо? Введіть число від 1 до 50.', reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='❌ Скасувати')]], resize_keyboard=True))

@dp.callback_query(F.data.removeprefix('ticket:').startswith('buy_'))
async def start_buy(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    event_id = int(callback.data.removeprefix('ticket:').split('_')[1])
    await state.clear()
    await state.update_data(ev_id=event_id, used_promo=None)
    event = await db.get_event(event_id)
    if not event or not event.get('is_active') or event.get('remaining_tickets', 0) <= 0:
        await state.clear()
        return await callback.answer('Подія або квитки вже недоступні', show_alert=True)
    if event.get('has_promo'):
        kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='➡️ Пропустити'), KeyboardButton(text='❌ Скасувати')]], resize_keyboard=True, one_time_keyboard=True)
        await callback.message.answer("🎟 Якщо маєш <b>промокод</b>, введи його зараз.\nЯкщо ні — тисни 'Пропустити':", reply_markup=kb, parse_mode='HTML')
        await state.set_state(OrderState.waiting_for_promocode)
    else:
        await proceed_to_buy_logic(callback.message, state, event)
    await callback.answer()

@dp.message(OrderState.waiting_for_promocode)
async def check_promocode(message: Message, state: FSMContext):
    if message.text == '❌ Скасувати':
        await state.clear()
        return await message.answer('👌 Бронювання скасовано.', reply_markup=main_kb(message.from_user.id))
    data = await state.get_data()
    event = await db.get_event(data['ev_id'])
    if message.text != '➡️ Пропустити':
        entered_promo = message.text.strip().upper()
        valid_promos = event['promocodes'].split(',') if event.get('promocodes') else []
        if entered_promo in valid_promos:
            await state.update_data(used_promo=entered_promo)
            await message.answer(f"✅ Промокод застосовано! Знижка <b>{event['promo_discount']} грн</b> на кожен квиток.", reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')
        else:
            kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='➡️ Пропустити'), KeyboardButton(text='❌ Скасувати')]], resize_keyboard=True)
            return await message.answer("❌ Невірний промокод. Спробуй ще раз або натисни 'Пропустити'.", reply_markup=kb)
    else:
        await message.answer('Продовжуємо без промокоду...', reply_markup=ReplyKeyboardRemove())
    await proceed_to_buy_logic(message, state, event)

@dp.message(F.text == '❌ Скасувати')
async def cancel_order(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return await message.answer('Ти зараз нічого не бронюєш 😅 Обирай події в меню 👇', reply_markup=main_kb(message.from_user.id))
    await state.clear()
    await message.answer('👌 Зрозумів, процес скасовано. Якщо передумаєш — я тут!', reply_markup=main_kb(message.from_user.id))


def order_payment_link(bank_link, order_id):
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
    parts = urlsplit((bank_link or '').strip())
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
        return None
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != 't']
    query.append(('t', f'NULP-{order_id}'))
    return urlunsplit(parts._replace(query=urlencode(query)))

async def process_order_payment(message: Message, state: FSMContext, is_organ=False):
    from urllib.parse import urlencode
    from app.core.config import ENABLE_PAYMENTS
    from app.features.ticketing.delivery import deliver_order
    from app.features.ticketing.logic import BookingError
    data = await state.get_data()
    event = await db.get_event(data['ev_id'])
    if not event:
        raise BookingError('Подія недоступна')
    keys = [seat.get('id') or f"{seat['row']}-{seat['seat']}" for seat in data.get('selected_seats', [])]
    if keys and set(keys) & set(await db.get_occupied_seats(event['id'])):
        raise BookingError('Одне з місць уже зайняте; відкрийте схему знову')
    order_id = await db.add_order(message.from_user.id, event['id'], int(data['qty']), ','.join(keys) if keys else None, 'organ_seats' if keys else None, data.get('used_promo'), data.get('friends', []))
    order = await db.get_order(order_id)
    await state.clear()
    await message.answer(f"Замовлення NULP-{order_id} збережено. Кількість: {order['ticket_count']}.", reply_markup=main_kb(message.from_user.id))
    user = await db.get_user(message.from_user.id)
    await sheets.sync_order(order,event,user)
    if order['status'] == 'confirmed':
        await deliver_order(order_id, bot, message.from_user.id)
        return
    buttons = [[InlineKeyboardButton(text='Надіслати квитанцію', callback_data=f'ticket:forgot_{order_id}')], [InlineKeyboardButton(text='Скасувати замовлення', callback_data=f'ticket:cancel_{order_id}')]]
    text = f"До оплати: {order['required_amount']} грн. Код у коментарі: NULP-{order_id}."
    link = order_payment_link(event.get('bank_link'), order_id)
    if link:
        buttons.insert(0, [InlineKeyboardButton(text='Перейти до оплати', url=link)])
        text += f"\nКартка: {event.get('card_number') or '-'}"
        if not ENABLE_PAYMENTS:
            text += '\nПісля оплати надішліть квитанцію: автоматичне підтвердження Monobank у цьому запуску не підключене.'
    else:
        text += '\nОрганізатор ще не вказав коректне HTTPS-посилання для оплати цієї події. Зверніться до підтримки.'
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.message(F.web_app_data)
async def handle_web_app_data(message: Message, state: FSMContext):
    raw_data = message.web_app_data.data
    current_state = await state.get_state()
    data = await state.get_data()
    logger.debug('Ticket flow checkpoint')
    if current_state == 'AddEventState:picking_seats':
        if not raw_data or raw_data == 'null':
            return await message.answer('⚠️ Місця не обрано.')
        seat_ids = raw_data.split('|')
        qty = len(seat_ids)
        await state.update_data(selected_seats=seat_ids, total_tickets=qty)
        await message.answer(f"✅ Обрано <b>{qty}</b> місць для продажу.\n\nТепер введи точну назву локації (напр. 'Органний зал, центральний вхід'):", reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')
        await state.set_state(AddEventState.location)
        return
    if raw_data.startswith('admin_seat|'):
        _, ev_id_str, full_id = raw_data.split('|')
        id_parts = full_id.split('-')
        if len(id_parts) == 3:
            zone, row, seat = (id_parts[0], id_parts[1], id_parts[2])
        else:
            zone, row, seat = ('Партер', id_parts[0], id_parts[1])
        row = full_id.rsplit('-', 1)[0]
        info = await db.get_seat_info(int(ev_id_str), row, seat)
        if not info:
            return await message.answer(f'ℹ️ Місце {full_id} не знайдено або вже вільне.')
        event = await db.get_event(int(ev_id_str))
        username = f"@{info['username']}" if info['username'] else 'Без юзернейму'
        text = f"🛠 <b>Деталі квитка</b>\n\n🎫 <b>Подія:</b> {event['title']}\n📍 <b>Місце:</b> {zone}, Ряд {row}, Місце {seat}\n\n👤 <b>Покупець:</b> {info['first_name']} {info['last_name']} ({username})\n📦 <b>ID Замовлення:</b> #{info['order_id']}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='❌ Скасувати цей квиток', callback_data='ticket:' + f"adm_cancel_{info['order_id']}_{row}_{seat}")]])
        return await message.answer(text, reply_markup=kb, parse_mode='HTML')
    try:
        if not data.get('ev_id'):
            return await message.answer('⚠️ Помилка: сесія застаріла (можливо, бот перезавантажився). Будь ласка, відкрий список подій і почни бронювання спочатку.', reply_markup=main_kb(message.from_user.id))
        selected_seats = []
        seat_items = raw_data.split('|')
        for item in seat_items:
            parts = item.split('-')
            if len(parts) == 3:
                selected_seats.append({'id': item, 'zone': parts[0], 'row': parts[1], 'seat': parts[2]})
            elif len(parts) == 2:
                selected_seats.append({'id': item, 'zone': 'Партер', 'row': parts[0], 'seat': parts[1]})
        qty = len(selected_seats)
        if qty == 0:
            return await message.answer('⚠️ Не обрано жодного місця.')
        await state.update_data(qty=qty, selected_seats=selected_seats)
        if qty == 1:
            await process_order_payment(message, state, is_organ=True)
        else:
            await state.update_data(total_friends=qty - 1, current_friend=1, friends=[])
            await message.answer(f"👥 Оскільки ти береш {qty} квитків, нам потрібні дані твоїх друзів.\n\nВведи Прізвище, Ім'я та @тег для <b>1-го друга</b>:", parse_mode='HTML')
            await state.set_state(OrderState.waiting_for_friend_data)
    except Exception as e:
        await message.answer(f'⚠️ Помилка обробки даних: {e}')

@dp.message(OrderState.waiting_for_quantity)
async def set_qty(message: Message, state: FSMContext):
    if message.text in ['Доступні події', 'Адмін-панель']:
        await state.clear()
        if message.text == 'Доступні події':
            return await list_events(message)
        else:
            return await admin_panel(message)
    if not message.text.isdigit() or int(message.text) <= 0:
        return await message.answer('⚠️ <b>Помилка:</b> Будь ласка, введи коректне число квитків (більше нуля)!', parse_mode='HTML')
    qty = int(message.text)
    data = await state.get_data()
    event = await db.get_event(data['ev_id'])
    if qty > event['remaining_tickets']:
        return await message.answer(f"❌ Ти не можеш взяти стільки. Залишилось всього <b>{event['remaining_tickets']}</b> квитків.", parse_mode='HTML')
    if qty == 1:
        await state.update_data(qty=qty)
        await process_order_payment(message, state)
    else:
        await state.update_data(qty=qty, total_friends=qty - 1, current_friend=1, friends=[])
        await message.answer(f"👥 Оскільки ти береш {qty} квитків, нам потрібні дані твоїх друзів.\n\nВведи Прізвище, Ім'я та @тег для <b>1-го друга</b> (наприклад: <i>Шевченко Тарас @taras123</i>):", parse_mode='HTML')
        await state.set_state(OrderState.waiting_for_friend_data)

@dp.message(OrderState.waiting_for_friend_data)
async def process_friend_data(message: Message, state: FSMContext):
    data = await state.get_data()
    friends = data.get('friends', [])
    friends.append(message.text)
    current = data['current_friend']
    total = data['total_friends']
    if current < total:
        await state.update_data(friends=friends, current_friend=current + 1)
        await message.answer(f'Введи дані для <b>{current + 1}-го друга</b>:', parse_mode='HTML')
    else:
        await state.update_data(friends=friends)
        is_organ = 'selected_seats' in data
        await process_order_payment(message, state, is_organ)

@dp.callback_query(F.data.removeprefix('ticket:').startswith('forgot_'))
async def forgot_code_handler(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.removeprefix('ticket:').split('_')[1])
    await state.update_data(manual_order_id=order_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer('Нічого страшного! Надішли сюди скріншот або PDF-квитанцію, і адмін підтвердить оплату вручну 👇')
    await state.set_state(OrderState.waiting_for_proof)

@dp.message(OrderState.waiting_for_proof, F.photo | F.document)
async def get_proof(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get('manual_order_id')
    if not order_id:
        await state.clear()
        return await message.answer('⚠️ Помилка: замовлення не знайдено. Спробуй почати бронювання знову.')
    order = await db.get_order(order_id)
    if not order:
        await state.clear()
        return await message.answer('⚠️ Замовлення не знайдено в базі даних.')
    event = await db.get_event(order['event_id'])
    user = await db.get_user(message.from_user.id)
    username = user['username'] if user['username'] else 'Без_юзернейму'
    qty = order['ticket_count']
    f_id = message.photo[-1].file_id if message.photo else message.document.file_id
    f_type = 'photo' if message.photo else 'document'
    await db.attach_proof_to_order(order_id, f_id, f_type)
    await sheets.update_payment_in_sheet(event['title'], order_id, 'Очікує підтвердження', event['venue_type'])
    caption = f"📸 <b>Ручна перевірка квитанції!</b> (Замовлення #{order_id})\n\n👤 Студент: {user['last_name']} {user['first_name']} (@{username})\n📚 Інститут/Група: {user['institute']}, {user['student_group']}\n🎟 Кількість квитків: {qty} шт.\n🎉 Подія: {event['title']}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='✅ Підтвердити', callback_data='ticket:' + f'conf_{order_id}')], [InlineKeyboardButton(text='❌ Відхилити', callback_data='ticket:' + f'reje_{order_id}')]])
    for admin in await get_admin_ids():
        try:
            if f_type == 'photo':
                await bot.send_photo(admin, f_id, caption=caption, reply_markup=kb, parse_mode='HTML')
            else:
                await bot.send_document(admin, f_id, caption=caption, reply_markup=kb, parse_mode='HTML')
        except Exception as e:
            logger.debug('Ticket flow checkpoint')
    await message.answer('⏳ <b>Квитанцію прийнято та надіслано адміністратору!</b>\nПісля перевірки ми надішлемо тобі підтвердження.', parse_mode='HTML')
    await state.clear()

@dp.message(OrderState.waiting_for_proof)
async def wrong_proof_format(message: Message, state: FSMContext):
    await message.answer('Надішліть фото або PDF-квитанцію. /cancel скасовує діалог.')


@dp.message(Command("tickets"))
async def tickets_command(message: Message, state: FSMContext):
    await state.clear()
    await list_events(message)

@dp.callback_query(F.data == "ticket:home")
async def tickets_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await list_events(callback.message)
    await callback.message.answer("Оберіть подію або перегляньте свої замовлення.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Мої замовлення",callback_data="ticket:orders")],
        [InlineKeyboardButton(text="Головне меню",callback_data="main_menu")]]))

@dp.callback_query(F.data == "ticket:orders")
async def my_orders(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    rows=await db.pool.fetch("SELECT o.*,e.title,e.bank_link FROM orders o JOIN events e ON e.id=o.event_id WHERE o.user_id=$1 ORDER BY o.id DESC LIMIT 30",callback.from_user.id)
    await callback.answer()
    if not rows:
        return await callback.message.answer("Замовлень ще немає.")
    for row in rows:
        buttons=[]
        if row['status']=='confirmed':
            buttons.append([InlineKeyboardButton(text="Отримати квитки",callback_data=f"ticket:deliver_{row['id']}")])
        elif row['status'] in {'pending','pending_manual'}:
            link = order_payment_link(row.get('bank_link'), row['id'])
            if link:
                buttons.append([InlineKeyboardButton(text='Перейти до оплати', url=link)])
            buttons.append([InlineKeyboardButton(text="Надіслати квитанцію",callback_data=f"ticket:forgot_{row['id']}")])
            buttons.append([InlineKeyboardButton(text="Скасувати",callback_data=f"ticket:cancel_{row['id']}")])
        await callback.message.answer(f"NULP-{row['id']} | {row['title']}\nКвитків: {row['ticket_count']} | Статус: {row['status']}\nСплачено: {row['paid_amount']} / {row['required_amount']} грн",reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None)

@dp.callback_query(F.data.startswith("ticket:deliver_"))
async def redeliver(callback: CallbackQuery):
    from app.features.ticketing.delivery import deliver_order
    order_id=int(callback.data.rsplit('_',1)[1])
    order=await db.get_order(order_id)
    if not order or order['user_id']!=callback.from_user.id:
        return await callback.answer("Замовлення недоступне",show_alert=True)
    await callback.answer()
    await deliver_order(order_id,bot,callback.from_user.id)

@dp.callback_query(F.data.startswith("ticket:cancel_"))
async def cancel_pending_order(callback: CallbackQuery):
    order_id=int(callback.data.rsplit('_',1)[1])
    order=await db.get_order(order_id)
    if not order or order['user_id']!=callback.from_user.id or order['status'] not in {'pending','pending_manual'}:
        return await callback.answer("Це замовлення не можна скасувати",show_alert=True)
    changed=await db.update_order_status(order_id,'cancelled')
    await callback.answer("Скасовано" if changed else "Замовлення вже опрацьовано",show_alert=True)

@dp.callback_query(F.data.startswith('ticket:pick:'))
async def inline_seat_action(callback: CallbackQuery, state: FSMContext, session):
    from app.features.ticketing.seat_picker import picker_keyboard
    from app.shared.admin_filter import AdminFilter
    current = await state.get_state()
    data = await state.get_data()
    admin = data.get('picker_admin', False)
    expected = AddEventState.picking_seats.state if admin else OrderState.choosing_seats.state
    if current != expected or not data.get('picker_keys'):
        return await callback.answer('Вибір застарів. Почніть знову.', show_alert=True)
    if admin and not await AdminFilter()(callback, session):
        return await callback.answer('Доступ заборонено', show_alert=True)
    action = callback.data.split(':')[2]
    keys = data['picker_keys']
    selected = list(data.get('picker_selected', []))
    occupied = set() if admin else set(await db.get_occupied_seats(data['ev_id']))
    page = data.get('picker_page', 0)
    if action == 'cancel':
        await state.clear()
        await callback.message.edit_text('Вибір скасовано.')
        return await callback.answer()
    if action == 'toggle':
        index = int(callback.data.split(':')[3])
        if not 0 <= index < len(keys):
            return await callback.answer('Недійсне місце', show_alert=True)
        key = keys[index]
        if key in occupied:
            return await callback.answer('Місце недоступне', show_alert=True)
        if key in selected:
            selected.remove(key)
        elif not admin and len(selected) >= 50:
            return await callback.answer('Максимум 50 квитків', show_alert=True)
        else:
            selected.append(key)
    elif action == 'page':
        page = max(0, min(int(callback.data.split(':')[3]), (len(keys)-1)//24))
    elif action == 'done':
        if not selected:
            return await callback.answer('Оберіть хоча б одне місце', show_alert=True)
        if set(selected) & occupied:
            selected = [key for key in selected if key not in occupied]
            await state.update_data(picker_selected=selected)
            await callback.message.edit_reply_markup(reply_markup=picker_keyboard(keys, selected, occupied, page))
            return await callback.answer('Зайняті місця прибрано. Перевірте вибір.', show_alert=True)
        if admin:
            await state.update_data(selected_seats=selected, total_tickets=len(selected))
            await state.set_state(AddEventState.location)
            await callback.message.edit_text(f'Обрано місць: {len(selected)}. Введіть точну адресу/локацію:')
        else:
            seats = [{'id': key, 'row': key.rsplit('-',1)[0], 'seat': key.rsplit('-',1)[1]} for key in selected]
            await state.update_data(qty=len(seats), selected_seats=seats)
            await callback.message.edit_reply_markup(reply_markup=None)
            message = callback.message.model_copy(update={'from_user': callback.from_user}).as_(callback.bot)
            if len(seats) == 1:
                await process_order_payment(message, state, is_organ=True)
            else:
                await state.update_data(total_friends=len(seats)-1, current_friend=1, friends=[])
                await state.set_state(OrderState.waiting_for_friend_data)
                await message.answer("Введіть прізвище, ім'я та @тег першого друга:")
        return await callback.answer()
    await state.update_data(picker_selected=selected, picker_page=page)
    await callback.message.edit_reply_markup(reply_markup=picker_keyboard(keys, selected, occupied, page))
    await callback.answer()
