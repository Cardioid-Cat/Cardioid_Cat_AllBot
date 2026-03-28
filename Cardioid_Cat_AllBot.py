import asyncio, os, json
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Данные из окружения
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
TARGET_GROUP_ID = -1003801387499
DB_FILE = "members_db.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- РАБОТА С БАЗОЙ УЧАСТНИКОВ ---

def load_members():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            try:
                data = json.load(f)
                return {int(k): set(v) for k, v in data.items()}
            except: return {}
    return {}

def save_members(data):
    serializable_data = {k: list(v) for k, v in data.items()}
    with open(DB_FILE, "w") as f:
        json.dump(serializable_data, f)

chat_members = load_members()

# --- ФУНКЦИЯ УВЕДОМЛЕНИЯ ПО РАСПИСАНИЮ ---

async def send_kv_reminder():
    # Проверяем, есть ли кого упоминать в нужной группе
    if TARGET_GROUP_ID in chat_members and chat_members[TARGET_GROUP_ID]:
        mentions = "".join([f'<a href="tg://user?id={uid}">\u2060</a>' for uid in chat_members[TARGET_GROUP_ID]])
        text = f"📢 <b>Внимание всем!</b> Сегодня играем КВ! ⚡️{mentions}"
    else:
        text = "📢 <b>Внимание всем!</b> Сегодня играем КВ! ⚡️"
    
    try:
        await bot.send_message(TARGET_GROUP_ID, text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка рассылки: {e}")

# --- ОБРАБОТЧИКИ ---

@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def track_and_call(m: types.Message):
    chat_id = m.chat.id
    user_id = m.from_user.id
    
    # Запоминаем участника
    if chat_id not in chat_members:
        chat_members[chat_id] = set()
    
    if not m.from_user.is_bot and user_id not in chat_members[chat_id]:
        chat_members[chat_id].add(user_id)
        save_members(chat_members)
    
    # Ручной вызов
    if m.text and ("@all" in m.text.lower() or "@все" in m.text.lower()):
        if chat_id in chat_members and chat_members[chat_id]:
            mentions = "".join([f'<a href="tg://user?id={uid}">\u2060</a>' for uid in chat_members[chat_id]])
            await m.answer(f"📢 <b>Внимание всем!</b> ⚡️{mentions}", parse_mode="HTML")

# --- ЗАПУСК ---

async def main():
    # Настройка планировщика (МСК)
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(
        send_kv_reminder, 
        trigger='cron', 
        day_of_week='thu,fri,sat,sun', 
        hour=22, 
        minute=0
    )
    scheduler.start()

    # Веб-сервер для Render
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Cardioid_Cat Bot Active"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 
