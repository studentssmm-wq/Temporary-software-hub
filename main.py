import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# Створюємо простий веб-сервер для Render


class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")


def run_dummy_server():
    # Render за замовчуванням очікує порт 10000
    server = HTTPServer(('0.0.0.0', 10000), DummyHandler)
    server.serve_forever()


# Запускаємо сервер в окремому фоновому потоці
threading.Thread(target=run_dummy_server, daemon=True).start()

# === ДАЛІ ЙДЕ ВАШ ЗВИЧАЙНИЙ КОД БОТА ===
# наприклад:
# if name == 'main':
#     asyncio.run(main())
