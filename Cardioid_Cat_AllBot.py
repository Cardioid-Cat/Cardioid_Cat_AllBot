import asyncio
import os
import json
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

# НОВЫЙ ID БЕСЕДЫ "ЧУМОВЫЕ ТРЕНИРОВКИ"
GROUP_ID = -1003773374182 
DB_TAG = "#DATABASE_EXERCISE_BOT#"

bot = Bot(token=TOKEN)
dp = Dispatcher()

NAME_MAP = {"А": "Артём", "Л": "Лиза", "В": "Вова", "Н": "Настя", "И": "Игорь"}
EX_MAP = {
    "отж": "отжиманий", "прис": "приседаний", "план": "планки",
    "вис": "вис", "гант": "гантели на спину", "подт": "подтягиваний"
}

# --- Вспомогательные функции ---

async def get_db_message():
    try:
        chat = await bot.get_chat(GROUP_ID)
        pinned = chat.pinned_message
        # Ищем тег базы данных в тексте закрепа
        if pinned and DB_TAG in (pinned.text or ""):
            return pinned
    except Exception as e:
        print(f"Ошибка при поиске закрепа: {e}")
        return None
    return None

async def load_data():
    msg = await get_db_message()
    if msg:
        try:
            # Пытаемся вытащить JSON данные, которые бот прячет в конце сообщения
            json_part = msg.text.split("📊")[-1].strip()
            return json.loads(json_part)
        except:
            # Если JSON нет (например, сообщение написано руками), возвращаем пустой словарь
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
    # Прячем данные для парсинга в последнюю строку
    lines.append(f"\n📊 {json.dumps(data, ensure_ascii=False)}")
    
    text = "\n".join(lines)
    msg = await get_db_message()
    
    if msg:
        await bot.edit_message_text(text, GROUP_ID, msg.message_id, parse_mode="HTML")
    else:
        # Если вдруг закреп пропал, создаем новый
        new_msg = await bot.send_message(GROUP_ID, text, parse_mode="HTML")
        await bot.pin_chat_message(GROUP_ID, new_msg.message_id)

# --- Обработка команд ---

# Фильтр: обрабатываем только если ID чата совпадает с нужной группой
@dp.message(F.chat.id == GROUP_ID, F.text.startswith(("!долг+", "!долг-")))
async def handle_debts(message: types.Message):
    parts = message.text.split()
    if len(parts) < 4: return

    action, name_init, val_str, ex_code = parts[0], parts[1].upper(), parts[2], parts[3].lower()
    
    try:
        val = int(val_str)
    except: return

    full_name = NAME_MAP.get(name_init)
    if not full_name: return

    data = await load_data()
    if full_name not in data: data[full_name] = {}
    
    current = data[full_name].get(ex_code, 0)
    data[full_name][ex_code] = (current + val) if "+" in action else max(0, current - val)

    await save_data(data)
    await message.answer(f"📢 <b>Внимание всем!</b>\nСписок обновлен в закрепе.")

# --- Рассылка и системное ---

async def send_kv_reminder():
    try:
        text = f"📢 <b>Внимание всем! ВСЕ ИГРАЕМ КВ СЕГОДНЯ!</b>"
        await bot.send_message(GROUP_ID, text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка рассылки: {e}")

async def health_check(request):
    return web.Response(text="Bot is running")

@dp.message(F.chat.id == GROUP_ID)
async def start_cmd(message: types.Message):
    if message.text == "/start":
        await message.answer("Бот настроен на эту беседу. Работаем!")

async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(send_kv_reminder, 'cron', day_of_week='thu,fri,sat,sun', hour=21, minute=0)
    scheduler.start()

    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
