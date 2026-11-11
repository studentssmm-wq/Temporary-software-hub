from app.core.config import ENABLE_SHEETS
import asyncio
import os
import json
import re
from datetime import datetime


SECTOR_MAP = {
    'A': {'c_start': 18, 'c_end': 25, 'r_start': 10, 'r_end': 31, 'h_off': 8},
    'B': {'c_start': 27, 'c_end': 34, 'r_start': 10, 'r_end': 31, 'h_off': 8},
    'C': {'c_start': 36, 'c_end': 43, 'r_start': 10, 'r_end': 31, 'h_off': 8},
    'D_row24': {'c_start': 18, 'c_end': 43, 'r_start': 36, 'r_end': 36},
    'D_main':  {'c_start': 21, 'c_end': 40, 'r_start': 37, 'r_end': 40, 'h_off': 12},
    'Balcony_main': {'c_start': 14, 'c_end': 39, 'r_start': 53, 'r_end': 58, 'h_off': 52},
    'Balcony_L': {'c_start': 6, 'c_end': 8, 'r_start': 31, 'r_end': 48, 'h_off': 30},
    'Balcony_R': {'c_start': 52, 'c_end': 54, 'r_start': 31, 'r_end': 49, 'h_off': 30}
}

def spreadsheet_url(venue_type=None):
    if venue_type == 'assembly_hall':
        return os.getenv('SPREADSHEET_GALA_URL', '') or os.getenv('SPREADSHEET_URL', '')
    return os.getenv('SPREADSHEET_URL', '')


def get_client():
    if not ENABLE_SHEETS:
        return None
    global gspread
    import gspread
    from google.oauth2.service_account import Credentials
    try:
        creds_json = os.getenv("GOOGLE_CREDS_JSON")
        if not creds_json: return None
        creds_dict = json.loads(creds_json)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        print("Google Sheets authentication failed")
        return None

def translate_coords_to_id(row, col):
    for zone in ['A', 'B', 'C']:
        m = SECTOR_MAP[zone]
        if m['r_start'] <= row <= m['r_end'] and m['c_start'] <= col <= m['c_end']:
            return f"{zone}-{row - m['h_off']}-{col - (m['c_start'] - 1)}"
    m = SECTOR_MAP['D_row24']
    if row == m['r_start'] and m['c_start'] <= col <= m['c_end']:
        return f"D-24-{col - 17}"
    m = SECTOR_MAP['D_main']
    if m['r_start'] <= row <= m['r_end'] and m['c_start'] <= col <= m['c_end']:
        return f"D-{row - m['h_off']}-{col - 20}"
    if SECTOR_MAP['Balcony_L']['r_start'] <= row <= SECTOR_MAP['Balcony_L']['r_end'] and 6 <= col <= 8:
        return f"ЛБ-{row - 30}-{col - 5}"
    if SECTOR_MAP['Balcony_R']['r_start'] <= row <= SECTOR_MAP['Balcony_R']['r_end'] and 52 <= col <= 54:
        return f"ПБ-{row - 30}-{col - 51}"
    m = SECTOR_MAP['Balcony_main']
    if m['r_start'] <= row <= m['r_end'] and m['c_start'] <= col <= m['c_end']:
        return f"Балкон-{row - m['h_off']}-{col - 13}"
    return None

def _get_or_create_worksheet(event_title, venue_type):
    client = get_client()
    if not client: return None
    try:
        url = spreadsheet_url(venue_type)
        doc = client.open_by_url(url)
        try:
            worksheet = doc.worksheet(event_title)
        except gspread.exceptions.WorksheetNotFound:

            if venue_type in ['organ_hall', 'assembly_hall']:
                headers = ["ID Замовлення", "Дата", "Прізвище", "Ім'я", "Telegram", "Інститут", "Сектор", "Ряд", "Місце", "Статус", "Промокод", "Квиток забрано"]
                cols = 12
            else:
                headers = ["ID Замовлення", "Дата", "Прізвище", "Ім'я", "Telegram", "Інститут", "Група", "К-сть квитків", "Статус", "Промокод"]
                cols = 10

            worksheet = doc.add_worksheet(title=event_title, rows="1000", cols=str(cols))
            worksheet.append_row(headers)
        return worksheet
    except Exception as e:
        print("Google spreadsheet unavailable")
        return None

def _add_order(event_title, order_id, last_name, first_name, username, institute, group, qty, status, venue_type, promocode="-"):
    try:
        ws = _get_or_create_worksheet(event_title, venue_type)
        if not ws: return

        tg = f"@{username}" if username != "-" else "-"


        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if venue_type in ['organ_hall', 'assembly_hall']:
            row_v, seat_v = "-", "-"
            match = re.search(r'Р(.+?)М(\S+)', status)
            if match:
                row_v, seat_v = match.group(1), match.group(2)



            ws.append_row([order_id, now_str, last_name, first_name, tg, institute, group, row_v, seat_v, status, promocode, "Ні"])
        else:
            ws.append_row([order_id, now_str, last_name, first_name, tg, institute, group, qty, status, promocode])
    except Exception as e:
        print("Google Sheets order synchronization failed")

async def add_order_to_sheet(*args):
    await asyncio.to_thread(_add_order, *args)

def _update_cell_in_sheet(event_title, order_id, status, venue_type):
    try:
        ws = _get_or_create_worksheet(event_title, venue_type)
        if not ws: return

        cells = ws.findall(str(order_id), in_column=1)
        if not cells: return


        status_col = 10 if venue_type in ['organ_hall', 'assembly_hall'] else 9

        for cell in cells:
            ws.update_cell(cell.row, status_col, status)
    except Exception as e:
        print("Google Sheets status synchronization failed")

async def update_payment_in_sheet(event_title, order_id, status, venue_type):
    await asyncio.to_thread(_update_cell_in_sheet, event_title, order_id, status, venue_type)

async def cancel_seat_in_sheet(event_title, order_id, row, seat, venue_type):
    await asyncio.to_thread(_update_cell_in_sheet, event_title, order_id, "🔴 СКАСОВАНО", venue_type)

def _get_occupied_from_sheet(event_title, venue_type):
    client = get_client()
    if not client: return []
    try:
        url = spreadsheet_url(venue_type)
        sheet_name = "РОЗСАДКА" if venue_type == 'assembly_hall' else "Схема залу"
        doc = client.open_by_url(url)
        ws = doc.worksheet(sheet_name)
        res = doc.fetch_sheet_metadata({'includeGridData': True})
        sheet_data = next(s for s in res['sheets'] if s['properties']['title'] == sheet_name)
        row_data = sheet_data['data'][0].get('rowData', [])
        occupied = []
        for r_idx, row in enumerate(row_data, 1):
            values = row.get('values', [])
            for c_idx, cell in enumerate(values, 1):
                bg = cell.get('userEnteredFormat', {}).get('backgroundColor', {})
                if bg and (bg.get('red', 1) < 1 or bg.get('green', 1) < 1 or bg.get('blue', 1) < 1):
                    seat_id = translate_coords_to_id(r_idx, c_idx)
                    if seat_id: occupied.append(seat_id)
        return occupied
    except: return []

async def get_occupied_from_sheet(event_title, venue_type):
    return await asyncio.to_thread(_get_occupied_from_sheet, event_title, venue_type)

async def upsert_user_in_registry(last_name, first_name, username, institute, group):
    await asyncio.to_thread(_upsert_user_in_registry, last_name, first_name, username, institute, group)

def _upsert_user_in_registry(last_name, first_name, username, institute, group):
    try:
        client = get_client()
        if not client: return
        doc = client.open_by_url(os.getenv("SPREADSHEET_URL", ""))
        ws = doc.sheet1
        tag = f"@{username}" if username else "-"
        try:
            cell = ws.find(tag, in_column=3)
            if cell:
                ws.update(f"A{cell.row}:B{cell.row}", [[last_name, first_name]])
                ws.update(f"D{cell.row}:E{cell.row}", [[institute, group]])
                return
        except: pass
        ws.append_row([last_name, first_name, tag, institute, group])
    except: pass

async def sync_order(order, event, user):
    if not ENABLE_SHEETS:
        return
    friends = json.loads(order.get("friends") or "[]")
    keys = (order.get("file_id") or "").split(",") if order.get("file_type") == "organ_seats" else []
    status = "Підтверджено" if order["status"] == "confirmed" else "Очікує оплати"
    if keys:
        for index,key in enumerate(keys):
            parts=key.rsplit("-",2)
            if len(parts)==3:
                zone,row,seat=parts
            else:
                zone="Партер"
                row,seat=parts
            await add_order_to_sheet(event["title"],order["id"],user["last_name"] if index==0 else "Гість",
                user["first_name"] if index==0 else friends[index-1] if index-1<len(friends) else "Гість",
                user["username"] or "-" if index==0 else "-",user["institute"] if index==0 else "Гість",zone,1,
                f"{status} (Р{row}М{seat})",event["venue_type"],order.get("promocode") or "-")
    else:
        await add_order_to_sheet(event["title"],order["id"],user["last_name"],user["first_name"],user["username"] or "-",
            user["institute"],user["student_group"],1,status,event["venue_type"],order.get("promocode") or "-")
        for friend in friends:
            await add_order_to_sheet(event["title"],order["id"],"Гість",friend,"-","Гість",user["username"] or "-",1,status,event["venue_type"],order.get("promocode") or "-")
