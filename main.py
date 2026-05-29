import asyncio
import random
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- МИНИ-ВЕБ-СЕРВЕР ДЛЯ ОБХОДА ПРОВЕРОК KOYEB ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is running 24/7!")

    def log_message(self, format, *args):
        return  # Отключаем лишний спам в логах

def run_health_server():
    # Koyeb передает порт в переменную окружения PORT. Если её нет, берем 8000
    port = int(os.getenv("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"Health-check сервер запущен на порту {port}")
    server.serve_forever()
# ------------------------------------------------

# КОНФИГ (Берем токен из переменных окружения для безопасности)
TOKEN = os.getenv("BOT_TOKEN")
GAS_URL = "https://script.google.com/macros/s/AKfycbweAA6W4pDVF7bg3w6J2EqPrFFvcrsbJw5gy4_MshYxu-ZuXxjfgTT04zHvTm4Zf1PB/exec"
IMAGE_URL = "https://docs.google.com/uc?export=view&id=1n34el_Xj4XufJavILI1h3cJUNu76rsmd"

bot = Bot(token=TOKEN)
dp = Dispatcher()

def api_call(action, data):
    try:
        return requests.post(GAS_URL, json={"action": action, **data}).json()
    except Exception as e:
        print(f"Ошибка API: {e}")
        return {}

@dp.message(Command("start"))
async def start(msg: types.Message):
    login_name = msg.from_user.username if msg.from_user.username else f"U{msg.from_user.id}"
    user = api_call("checkUser", {"chatId": msg.chat.id, "username": login_name})
    
    if user.get("exists"):
        caption = (
            f"✨ <b>С возвращением!</b>\n\n"
            f"🔑 <b>Логин:</b> <code>{user.get('login', 'Не найден')}</code>\n"
            f"🔑 <b>Пароль:</b> <code>{user.get('pass', 'Не найден')}</code>"
        )
        await bot.send_photo(msg.chat.id, photo=IMAGE_URL, caption=caption, parse_mode="HTML")
    else:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🚫 Нет промокода", callback_data="skip")]])
        await bot.send_photo(msg.chat.id, photo=IMAGE_URL, caption="👋 <b>Привет!</b> Введи промокод:", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "skip")
async def skip_promo(cb: types.CallbackQuery):
    await cb.message.delete()
    await register_process(cb.message, "БЕЗ_ПРОМОКОДА", cb.from_user)

@dp.message(F.text & ~F.text.startswith("/"))
async def text_promo(msg: types.Message):
    await register_process(msg, msg.text, msg.from_user)

async def register_process(msg, promo, user):
    login = (user.username if user.username else f"U{user.id}")[:8].upper()
    password = f"{login[:3]}!{random.randint(1000,9999)}"
    ref = f"{login}{random.randint(1000,9999)}"
    
    api_call("register", {"chatId": msg.chat.id, "login": login, "pass": password, "ref": ref})
    
    caption = (
        f"🎉 <b>Регистрация завершена!</b>\n\n"
        f"🔑 <b>Логин:</b> <code>{login}</code>\n"
        f"🔑 <b>Пароль:</b> <code>{password}</code>\n"
        f"🎟 <b>Реф:</b> <code>{ref}</code>"
    )
    await bot.send_photo(msg.chat.id, photo=IMAGE_URL, caption=caption, parse_mode="HTML")

async def main():
    # Запускаем наш фейковый веб-сервер в фоновом потоке
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # Запускаем самого бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
