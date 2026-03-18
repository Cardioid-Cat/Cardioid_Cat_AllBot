import asyncio
import os
import json
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web

# Конфигурация из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

# ЖЕСТКАЯ ПРИВЯЗКА ID (Чумовые тренировки)
TARGET_GROUP_ID = -1003773374182 
DB_TAG = "#DATABASE_EXERCISE_BOT#"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Карты имен и упражнений
NAME_MAP = {"А": "Артём", "Л": "Лиза", "В": "Вова", "Н": "Настя", "И": "Игорь"}
EX_MAP = {
    "отж": "отжиманий", "прис": "приседаний", "план": "планки",
    "вис": "вис", "гант": "гантели на спину", "подт": "подтягиваний"
}

# --- Работа с базой данных в закрепе ---

async def get_db_message():
    try:
        chat = await bot.get_chat(TARGET_GROUP_ID)
        pinned = chat.pinned_message
        if pinned and DB_TAG in (pinned.text or ""):
            return pinned
    except Exception as e:
        print(f"Ошибка при поиске закрепа: {e}")
    return None

async def load_data():
    msg = await get_db_message()
    if msg:
        try:
            # Парсим JSON данные из последней строки сообщения
            json_part = msg.text.split("📊")[-1].strip()
            return json.loads(json_part)
        except:
            return {}
    return {}

async def save_data(data):
    lines = ["<b>📊 АКТУАЛЬНЫЕ ДОЛГИ</b>\n"]
    has_debts = False
    
    for name, exercises in data.items():
        ex_list = [f"{val} {EX_MAP.get(ex, ex)}" for ex, val in exercises.items() if val > 0]
        if ex_list:
            lines.append(f"• <b>{name}</b>: {', '.join(ex_list)}")
            has_debts = True
    
    if not has_debts:
        lines.append("Все долги закрыты! Красавчики.")

    lines.append(f"\n{DB_TAG}")
    lines.append(f"\n📊 {json.dumps(data, ensure_ascii=False)}")
    
    text = "\n".join(lines)
    msg = await get_db_message()
    
    try:
        if msg:
            await bot.edit_message_text(text, TARGET_GROUP_ID, msg.message_id, parse_mode="HTML")
        else:
            new_msg = await bot.send_message(TARGET_GROUP_ID, text, parse_mode="HTML")
            await bot.pin_chat_message(TARGET_GROUP_ID, new_msg.message_id)
    except Exception as e:
        print(f"Ошибка при сохранении текста: {e}")

# --- ОБРАБОТЧИКИ КОМАНД ---

# 1. @all и @все — работают в ЛЮБОМ чате
@dp.message(F.text.lower().contains("@all") | F.text.lower().contains("@все"))
async def call_everyone(message: types.Message):
    await message.answer("📢 <b>Внимание всем!</b> ⚡️", parse_mode="HTML")

# 2. Долги — работают ТОЛЬКО в целевой группе
@dp.message(F.text.startswith("!долг"))
async def handle_debts(message: types.Message):
    # Проверка чата
    if message.chat.id != TARGET_GROUP_ID:
        return

    parts = message.text.split()
    if len(parts) < 4:
        await message.answer("⚠️ Формат: !долг+ А 50 отж")
        return

    action, name_init, val_str, ex_code = parts[0], parts[1].upper(), parts[2], parts[3].lower()
    
    try:
        val = int(val_str)
    except:
        await message.answer("⚠️ Ошибка: количество должно быть числом.")
        return

    full_name = NAME_MAP.get(name_init)
    if not full_name:
        await message.answer(f"⚠️ Имя '{name_init}' не найдено в списке (А, Л, В, Н, И).")
        return

    data = await load_data()
    if full_name not in data:
        data[full_name] = {}
    
    current = data[full_name].get(ex_code, 0)
    
    if "+" in action:
        data[full_name][ex_code] = current + val
    else:
        data[full_name][ex_code] = max(0, current - val)

    await save_data(data)
    await message.answer(f"✅ Данные обновлены для <b>{full_name}</b>. См. закреп.", parse_mode="HTML")

# --- СИСТЕМНЫЕ ФУНКЦИИ ---

async def send_kv_reminder():
    try:
        text = "📢 <b>Внимание всем! ВСЕ ИГРАЕМ КВ СЕГОДНЯ!</b>"
        await bot.send_message(TARGET_GROUP_ID, text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка рассылки КВ: {e}")

async def health_check(request):
    return web.Response(text="Bot is running")

async def main():
    # Планировщик КВ
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(send_kv_reminder, 'cron', day_of_week='thu,fri,sat,sun', hour=21, minute=0)
    scheduler.start()

    # Веб-сервер для Render (Health Check)
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    
    print("Бот успешно запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
