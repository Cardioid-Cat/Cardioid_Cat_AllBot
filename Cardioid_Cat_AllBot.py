import asyncio
import os
import json
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

TARGET_GROUP_ID = -1003773374182 
DB_TAG = "#DATABASE_EXERCISE_BOT#"

FOOTER_TEXT = (
    "\nРасчёт по долгам происходит только при свидетелях "
    "(минимум 3 из данной группы, +1 - тот, кто делает), либо на видео!"
)

# Функция для превращения текста "3:34" или числа секунд в общее кол-во секунд
def to_seconds(value):
    if isinstance(value, int):
        return value
    if isinstance(value, str) and ":" in value:
        try:
            parts = value.replace(" мин", "").split(":")
            return int(parts[0]) * 60 + int(parts[1])
        except:
            return 0
    return 0

# Функция для красивого вывода секунд в формат "М:СС мин"
def from_seconds(total_seconds):
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d} мин"

# АКТУАЛЬНЫЕ НАЧАЛЬНЫЕ ДАННЫЕ (в секундах для мат. расчетов)
INITIAL_DATA = {
    "Артём": {"отж": 175, "прис": 100, "план": 180, "вис": 360, "руб": 700},
    "Лиза": {"вис": 214, "гант": 85, "план": 171, "прис": 165},
    "Вова": {"план": 120, "гант": 50, "отж": 25, "прис": 100},
    "Настя": {"гант": 100, "отж": 100, "прис": 100},
    "Игорь": {"подт": 30, "план": 180, "прис": 100}
}

bot = Bot(token=TOKEN)
dp = Dispatcher()

EX_MAP = {
    "отж": "отжиманий", "прис": "приседаний", "план": "планка",
    "вис": "вис", "гант": "гантели на спину (каждая рука)", 
    "подт": "подтягиваний", "руб": "рублей"
}

# Упражнения, которые считаются как время
TIME_EXERCISES = ["план", "вис"]

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
            if val == 0: continue
            label = EX_MAP.get(ex, ex)
            
            # Если это время — выводим красиво (М:СС)
            if ex in TIME_EXERCISES:
                ex_list.append(f"{from_seconds(val)} {label}")
            else:
                ex_list.append(f"{val} {label}")
        
        if ex_list:
            lines.append(f"<b>{name}</b> - {', '.join(ex_list)}")
        else:
            lines.append(f"<b>{name}</b> - долгов нет")

    lines.append(FOOTER_TEXT)
    lines.append(f"\n📊 {json.dumps(data, ensure_ascii=False)}")
    
    text = "\n".join(lines)
    
    try:
        await bot.unpin_all_chat_messages(TARGET_GROUP_ID)
        new_msg = await bot.send_message(TARGET_GROUP_ID, text, parse_mode="HTML")
        await bot.pin_chat_message(TARGET_GROUP_ID, new_msg.message_id)
    except Exception as e:
        print(f"Ошибка закрепа: {e}")

# --- ОБРАБОТЧИКИ ---

@dp.message(F.text.lower().contains("@all") | F.text.lower().contains("@все"))
async def call_everyone(message: types.Message):
    await message.answer("📢 <b>Внимание всем!</b> ⚡️", parse_mode="HTML")

@dp.message(F.text.startswith("!добавить"))
async def add_person(message: types.Message):
    if message.chat.id != TARGET_GROUP_ID: return
    parts = message.text.split()
    if len(parts) < 2: return
    name, data = parts[1], await load_data()
    if name not in data:
        data[name] = {}
        await save_data(data)
        await message.answer(f"✅ {name} добавлен.")

@dp.message(F.text.startswith("!удалить"))
async def remove_person(message: types.Message):
    if message.chat.id != TARGET_GROUP_ID: return
    parts = message.text.split()
    if len(parts) < 2: return
    name, data = parts[1], await load_data()
    found_name = next((k for k in data.keys() if k.lower() == name.lower()), None)
    if found_name:
        del data[found_name]
        await save_data(data)
        await message.answer(f"❌ {found_name} удален.")

@dp.message(F.text.startswith("!долг"))
async def handle_debts(message: types.Message):
    if message.chat.id != TARGET_GROUP_ID: return
    parts = message.text.split()
    
    # Очистка: !долг- А очистить
    if len(parts) == 3 and parts[0] == "!долг-" and parts[2].lower() == "очистить":
        name_input = parts[1].upper()
        name_map = {"А": "Артём", "Л": "Лиза", "В": "Вова", "Н": "Настя", "И": "Игорь"}
        full_name = name_map.get(name_input, parts[1])
        data = await load_data()
        if full_name in data:
            data[full_name] = {}
            await save_data(data)
            return await message.answer(f"🧹 Долги {full_name} очищены.")

    if len(parts) < 4: return
    action, name_init, val_str, ex_code = parts[0], parts[1].upper(), parts[2], parts[3].lower()
    name_map = {"А": "Артём", "Л": "Лиза", "В": "Вова", "Н": "Настя", "И": "Игорь"}
    full_name = name_map.get(name_init, name_init)
    
    data = await load_data()
    if full_name not in data: data[full_name] = {}
    
    # Логика расчета
    current_val = to_seconds(data[full_name].get(ex_code, 0))
    
    # Если ввели время (1:30), переводим в секунды, если просто число — оставляем числом
    input_val = to_seconds(val_str) if ":" in val_str else int(val_str)

    if "+" in action:
        data[full_name][ex_code] = current_val + input_val
    else:
        data[full_name][ex_code] = max(0, current_val - input_val)

    await save_data(data)
    try: await message.delete()
    except: pass

async def main():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
