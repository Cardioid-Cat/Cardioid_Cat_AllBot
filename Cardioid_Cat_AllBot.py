import asyncio
import os
import json
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

TARGET_GROUP_ID = -1003773374182 
DB_TAG = "#DATABASE_EXERCISE_BOT#"

# Твой текст про расчет (футер)
FOOTER_TEXT = (
    "\nРасчёт по долгам происходит только при свидетелях "
    "(минимум 3 из данной группы, +1 - тот, кто делает), либо на видео!"
)

# ИСПРАВЛЕННЫЕ НАЧАЛЬНЫЕ ДАННЫЕ (как на скрине 01:24)
INITIAL_DATA = {
    "Артём": {"отж": 175, "прис": 100, "план": "3мин", "вис": "6мин", "деньги": "700р"},
    "Лиза": {"вис": "34 секунды", "гант": 85, "план": "2:51мин", "прис": 165, "вис_турник": "3 мин"},
    "Вова": {"план": "2мин", "гант": 50, "отж": 25, "прис": 100},
    "Настя": {"гант": 100, "отж": 100, "прис": 100},
    "Игорь": {"подт": 30, "план": "3мин", "прис": 100}
}

bot = Bot(token=TOKEN)
dp = Dispatcher()

NAME_MAP = {"А": "Артём", "Л": "Лиза", "В": "Вова", "Н": "Настя", "И": "Игорь"}
EX_MAP = {
    "отж": "отжиманий", "прис": "приседаний", "план": "планка",
    "вис": "вис", "гант": "гантели на спину (каждая рука)", 
    "подт": "подтягиваний", "деньги": "долг", "вис_турник": "вис на турнике"
}

async def get_db_message():
    try:
        chat = await bot.get_chat(TARGET_GROUP_ID)
        pinned = chat.pinned_message
        if pinned and DB_TAG in (pinned.text or ""):
            return pinned
    except: return None

async def load_data():
    msg = await get_db_message()
    if msg:
        try:
            json_part = msg.text.split("📊")[-1].strip()
            return json.loads(json_part)
        except: return INITIAL_DATA
    return INITIAL_DATA

async def save_data(data):
    lines = [f"{DB_TAG}", "<b>ДОЛГИ!!!</b>\n"]
    
    for name, exercises in data.items():
        ex_list = []
        for ex, val in exercises.items():
            label = EX_MAP.get(ex, ex)
            # Если значение число — пишем "50 отжиманий", если строка — "3мин планка"
            if isinstance(val, int):
                ex_list.append(f"{val} {label}")
            else:
                ex_list.append(f"{val} {label}")
        
        if ex_list:
            lines.append(f"<b>{name}</b> - {', '.join(ex_list)}")

    lines.append(FOOTER_TEXT)
    # Скрытая часть для базы данных
    lines.append(f"\n📊 {json.dumps(data, ensure_ascii=False)}")
    
    text = "\n".join(lines)
    
    try:
        await bot.unpin_all_chat_messages(TARGET_GROUP_ID)
        new_msg = await bot.send_message(TARGET_GROUP_ID, text, parse_mode="HTML")
        await bot.pin_chat_message(TARGET_GROUP_ID, new_msg.message_id)
    except Exception as e:
        print(f"Ошибка закрепа: {e}")

@dp.message(F.text.lower().contains("@all") | F.text.lower().contains("@все"))
async def call_everyone(message: types.Message):
    await message.answer("📢 <b>Внимание всем!</b> ⚡️", parse_mode="HTML")

@dp.message(F.text.startswith("!долг"))
async def handle_debts(message: types.Message):
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
        await message.answer("⚠️ Ошибка: количество должно быть целым числом.")
        return

    full_name = NAME_MAP.get(name_init)
    if not full_name: return

    data = await load_data()
    if full_name not in data: data[full_name] = {}
    
    current = data[full_name].get(ex_code, 0)
    # Если в базе строка (как "3мин"), а мы прибавляем число, сбрасываем в 0 и считаем
    if not isinstance(current, int): current = 0 
    
    if "+" in action:
        data[full_name][ex_code] = current + val
    else:
        data[full_name][ex_code] = max(0, current - val)

    await save_data(data)
    await message.delete()

async def health_check(request): return web.Response(text="Bot Active")

async def main():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
