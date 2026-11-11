
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
from aiogram.types import (Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, WebAppInfo, BufferedInputFile)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.features.ticketing.states import (AdminBroadcast, AdminEdit, EditProfile, OrderState,
    AddEventState, AdminBlacklist, AdminTickets)
from app.features.ticketing.runtime import db, bot, ADMIN_IDS, BLACKLIST_CACHE
from app.features.ticketing import sheets
from app.features.ticketing.ticket_generator import create_personalized_ticket
logger = logging.getLogger(__name__)

def main_kb(user_id):
    buttons = [[KeyboardButton(text='Доступні події'), KeyboardButton(text='Мій профіль')], [KeyboardButton(text='🏠 Головне меню')]]
    if user_id in ADMIN_IDS:
        buttons.append([KeyboardButton(text='Адмін-панель')])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def institute_kb():
    buttons = [[KeyboardButton(text='Я не студент'), KeyboardButton(text='Інший університет')], [KeyboardButton(text='ІНЕМ'), KeyboardButton(text='ІППО'), KeyboardButton(text='ІКТА')], [KeyboardButton(text='ІКНІ'), KeyboardButton(text='ІКТЕ'), KeyboardButton(text='ІМФН')], [KeyboardButton(text='ІГСН'), KeyboardButton(text='ІГДГ'), KeyboardButton(text='ІПМТ')], [KeyboardButton(text='ІМІТ'), KeyboardButton(text='ІАРД'), KeyboardButton(text='ІЕСК')], [KeyboardButton(text='ІВБІ'), KeyboardButton(text='ІХХТ'), KeyboardButton(text='ІБІБ')]]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Додати подію', callback_data='ticket:' + 'admin_add_event')], [InlineKeyboardButton(text='Редагувати подію', callback_data='ticket:' + 'admin_edit_list')], [InlineKeyboardButton(text='Видалити подію', callback_data='ticket:' + 'admin_del_list')], [InlineKeyboardButton(text='Розсилка', callback_data='ticket:' + 'admin_broadcast')], [InlineKeyboardButton(text='⚫ Чорний список', callback_data='ticket:' + 'admin_blacklist')], [InlineKeyboardButton(text='📎 Завантажити квитки (1шт + підпис)', callback_data='ticket:' + 'admin_upload_tickets')], [InlineKeyboardButton(text='📂 МАСОВЕ завантаження ПДФ', callback_data='ticket:' + 'admin_mass_upload')], [InlineKeyboardButton(text='🗺 Керування залом (Адмін)', callback_data='ticket:' + 'admin_manage_hall')]])

def get_organ_hall_kb(selected_seats: list):
    builder = InlineKeyboardBuilder()
    for r in range(1, 6):
        buttons = []
        for s in range(1, 9):
            seat_id = f'{r}_{s}'
            text = f'✅{r}-{s}' if seat_id in selected_seats else f'{r}-{s}'
            buttons.append(InlineKeyboardButton(text=text, callback_query_data=f'seat_toggle:{seat_id}'))
        builder.row(*buttons)
    builder.row(InlineKeyboardButton(text='✅ ГОТОВО (Зберегти)', callback_query_data='seats_done'))
    return builder.as_markup()
