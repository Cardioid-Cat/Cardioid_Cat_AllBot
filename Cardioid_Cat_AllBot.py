import asyncio, os, json
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
TARGET_GROUP_ID = -1003773374182 
DB_TAG = "#DATABASE_EXERCISE_BOT#"

TIME_EXERCISES = ["план", "вис"]
EX_MAP = {
    "отж": "отжиманий", "прис": "приседаний", "план": "планка",
    "вис": "вис", "гант": "гантелей на спину (каждая рука)", 
    "подт": "подтягиваний", "руб": "рублей"
}

# НАЧАЛЬНЫЕ ДАННЫЕ (Время сразу переведено в секунды)
INITIAL_DATA = {
    "Артём": {"отж": 175, "прис": 100, "план": 180, "вис": 360, "руб": 700},
    "Лиза": {"вис": 214, "гант": 85, "план": 171, "прис": 165},
    "Вова": {"план": 120, "гант": 50, "отж": 25, "прис": 100},
    "Настя": {"гант": 100, "отж": 100, "прис": 100},
    "Игорь": {"подт": 30, "план": 180, "прис": 100}
}

def smart_to_seconds(val, is_time_ex=False):
    if val is None: return 0
    s = str(val).lower().replace("мин", "").replace("сек", "").strip()
    try:
        if ":" in s:
            p = s.split(":")
            return int(p[0]) * 60 + int(p[1])
        num = int(float(s))
        # Если это время и введено число меньше 100 (например 3) -> это минуты
        if is_time_ex and num < 100:
            return num * 60
        return num
    except: return 0

def format_display(v, ex):
    if ex in TIME_EXERCISES:
        v = int(v)
        return f"{v // 60}:{v % 60:02d} мин"
    return str(v)

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def load_data():
    try:
        chat = await bot.get_chat(TARGET_GROUP_ID)
        if chat.pinned_message and DB_TAG in chat.pinned_message.text:
            json_part = chat.pinned_message.text.split("📊")[-1].strip()
            return json.loads(json_part)
    except: pass
    return INITIAL_DATA

async def save_data(data):
    lines = [DB_TAG, "<b>📊 АКТУАЛЬНЫЕ ДОЛГИ</b>\n"]
    for name, exs in data.items():
        res = []
        for e, v in exs.items():
            val = smart_to_seconds(v, e in TIME_EXERCISES)
            if val > 0:
                res.append(f"{format_display(val, e)} {EX_MAP.get(e, e)}")
        lines.append(f"• <b>{name}</b>: {', '.join(res) if res else 'долгов нет'}")
    
    lines.append("\n⚠️ <i>Расчёт по долгам происходит только при свидетелях (минимум 3 из группы + 1 делающий) или на видео!</i>")
    
    # Сохраняем чистый JSON
    clean_db = {n: {e: smart_to_seconds(v, e in TIME_EXERCISES) for e, v in ex_dict.items()} for n, ex_dict in data.items()}
    lines.append(f"\n📊 {json.dumps(clean_db, ensure_ascii=False)}")
    
    try:
        await bot.unpin_all_chat_messages(TARGET_GROUP_ID)
        msg = await bot.send_message(TARGET_GROUP_ID, "\n".join(lines), parse_mode="HTML")
        await bot.pin_chat_message(TARGET_GROUP_ID, msg.message_id)
    except: pass

@dp.message(F.text.startswith("!долг"))
async def handle(m: types.Message):
    if m.chat.id != TARGET_GROUP_ID: return
    p = m.text.split()
    if len(p) < 4: return
    
    n_map = {"А": "Артём", "Л": "Лиза", "В": "Вова", "Н": "Настя", "И": "Игорь"}
    name = n_map.get(p[1].upper(), p[1])
    val_str, ex = p[2], p[3].lower()
    
    if ex not in TIME_EXERCISES and ":" in val_str:
        return await m.answer(f"❌ {ex} — это не время, пиши числом!")

    data = await load_data()
    if name not in data: data[name] = {}
    
    is_time = ex in TIME_EXERCISES
    current = smart_to_seconds(data[name].get(ex, 0), is_time)
    input_val = smart_to_seconds(val_str, is_time)
    
    if "+" in p[0]:
        data[name][ex] = current + input_val
    else:
        data[name][ex] = max(0, current - input_val)

    await save_data(data)
    try: await m.delete()
    except: pass

@dp.message(F.text.in_(["@все", "@all"]))
async def call_all(m: types.Message):
    await m.answer("📢 <b>Внимание всем!</b> ⚡️", parse_mode="HTML")

async def main():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 
