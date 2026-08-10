import asyncio
import threading
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

# Імпортуємо вашу функцію запуску бота
from app.bot import start_bot

# === Створюємо простий веб-сервер для Render ===
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_dummy_server():
    # Отримуємо порт, який вимагає Render, або беремо 10000 за замовчуванням
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    print(f"Фейковий сервер запущено на порту {port}...")
    server.serve_forever()


# === ГОЛОВНИЙ ЗАПУСК ===
if __name__ == "__main__":
    # 1. Запускаємо фейковий сервер в окремому фоновому потоці
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    # 2. Запускаємо вашого бота
    asyncio.run(start_bot())
