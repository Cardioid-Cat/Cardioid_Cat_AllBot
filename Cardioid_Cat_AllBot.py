import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web

API_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# База данных
db_path = "members.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER, user_id INTEGER, name TEXT, PRIMARY KEY(chat_id, user_id))")
conn.commit()

# --- Крошечный веб-сервер для Render ---
async def handle(request):
    return web.Response(text="Bot is running!")

app = web.Application()
app.router.add_get('/', handle)

async def start_webserver():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', os.getenv("PORT", 10000))
    await site.start()
# ---------------------------------------

@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def collector(message: types.Message):
    cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", 
                   (message.chat.id, message.from_user.id, message.from_user.full_name))
    conn.commit()
    if message.text:
        msg_text = message.text.lower()
        if any(trigger in msg_text for trigger in ["@all", "/all", "@все", "/все"]):
            cursor.execute("SELECT user_id FROM users WHERE chat_id = ?", (message.chat.id,))
            users = cursor.fetchall()
            if users:
                mentions = "".join([f'<a href="tg://user?id={u[0]}">\u200b</a>' for u in users])
                await message.answer(f"📢 <b>Внимание всем!</b>{mentions}", parse_mode="HTML")

async def main():
    # Запускаем веб-сервер и бота одновременно
    await start_webserver()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())