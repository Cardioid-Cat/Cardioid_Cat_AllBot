import asyncio, os, json
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
# Имя файла для хранения базы
DB_FILE = "members_db.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ФУНКЦИИ РАБОТЫ С ФАЙЛОМ ---

def load_members():
    """Загружает участников из файла при старте"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            try:
                # Превращаем ключи обратно в INT (в JSON они всегда строки)
                data = json.load(f)
                return {int(k): set(v) for k, v in data.items()}
            except:
                return {}
    return {}

def save_members(data):
    """Сохраняет текущий список участников в файл"""
    # Множества (set) нельзя напрямую в JSON, превращаем в списки
    serializable_data = {k: list(v) for k, v in data.items()}
    with open(DB_FILE, "w") as f:
        json.dump(serializable_data, f)

# Загружаем данные в память при запуске скрипта
chat_members = load_members()

# --- ОБРАБОТЧИКИ ---

@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def track_members(m: types.Message):
    chat_id = m.chat.id
    user_id = m.from_user.id
    
    if chat_id not in chat_members:
        chat_members[chat_id] = set()
    
    if not m.from_user.is_bot and user_id not in chat_members[chat_id]:
        chat_members[chat_id].add(user_id)
        # Сохраняем в файл только когда появился НОВЫЙ человек
        save_members(chat_members)
    
    # Реакция на @all или @все
    if m.text and ("@all" in m.text.lower() or "@все" in m.text.lower()):
        await call_all_logic(m)

async def call_all_logic(m: types.Message):
    chat_id = m.chat.id
    if chat_id not in chat_members or not chat_members[chat_id]:
        return # Бот никого не знает, просто молчим

    # Формируем скрытые упоминания (невидимый символ \u2060)
    mentions = "".join([f'<a href="tg://user?id={uid}">\u2060</a>' for uid in chat_members[chat_id]])
    
    await m.answer(f"📢 <b>Внимание всем!</b> ⚡️{mentions}", parse_mode="HTML")

# --- ЗАПУСК ---

async def main():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Бот Cardioid_Cat в сети!"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
