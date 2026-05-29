import asyncio
import random
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command

# --- МИНИ ВЕБ-СЕРВЕР ДЛЯ RENDER (ЧТОБЫ БОТ РАБОТАЛ КРУГЛОСУТОЧНО) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is online!")
    def log_message(self, format, *args):
        return

def run_health_server():
    # Render автоматически передает порт в переменную PORT, если ее нет — берем 8000
    port = int(os.getenv("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()
# -----------------------------------------------------------------

# КОНФИГ
TOKEN = "8709985175:AAFgqaXrgyN4LnYD74Pd95ypj58AVx5qSWg"
GAS_URL = "https://script.google.com/macros/s/AKfycbweAA6W4pDVF7bg3w6J2EqPrFFvcrsbJw5gy4_MshYxu-ZuXxjfgTT04zHvTm4Zf1PB/exec"
IMAGE_URL = "https://docs.google.com/uc?export=view&id=1n34el_Xj4XufJavILI1h3cJUNu76rsmd"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Защита от двойных нажатий регистрации
processing_users = set()

def api_call(action, data):
    try:
        return requests.post(GAS_URL, json={"action": action, **data}, timeout=15).json()
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
            f"🔑 <b>Пароль:</b> <code>{user.get('pass', 'Не найден')}</code>\n"
            f"🎟 <b>Реф:</b> <code>{user.get('ref', 'Не найден')}</code>"
        )
        await bot.send_photo(msg.chat.id, photo=IMAGE_URL, caption=caption, parse_mode="HTML")
    else:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🚫 Нет промокода", callback_data="skip")]])
        await bot.send_photo(msg.chat.id, photo=IMAGE_URL, caption="👋 <b>Привет!</b> Введи промокод:", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "skip")
async def skip_promo(cb: types.CallbackQuery):
    await cb.answer()
    await cb.message.delete()
    await register_process(cb.message, "БЕЗ_ПРОМОКОДА", cb.from_user)

@dp.message(F.text & ~F.text.startswith("/"))
async def text_promo(msg: types.Message):
    await register_process(msg, msg.text.strip(), msg.from_user)

async def register_process(msg, promo, user):
    if user.id in processing_users:
        return
    processing_users.add(user.id)
    
    try:
        login = (user.username if user.username else f"U{user.id}")[:8].upper()
        password = f"{login[:3]}!{random.randint(1000,9999)}"
        
        # Передаем промокод в поле reqCode, чтобы гугл-таблица его увидела и выдала VIP!
        payload = {
            "chatId": msg.chat.id, 
            "login": login, 
            "pass": password, 
            "reqCode": promo if promo != "БЕЗ_ПРОМОКОДА" else ""
        }
        
        res = api_call("register", payload)
        final_ref = res.get("ref") if res.get("status") == "ok" else f"{login}{random.randint(1000,9999)}"
        
        caption = (
            f"🎉 <b>Регистрация завершена!</b>\n\n"
            f"🔑 <b>Логин:</b> <code>{login}</code>\n"
            f"🔑 <b>Пароль:</b> <code>{password}</code>\n"
            f"🎟 <b>Реф:</b> <code>{final_ref}</code>"
        )
        await bot.send_photo(msg.chat.id, photo=IMAGE_URL, caption=caption, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка при регистрации: {e}")
    finally:
        processing_users.discard(user.id)

async def main():
    # 1. Запускаем фоновый веб-сервер для Render
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # 2. Запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
