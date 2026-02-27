import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiohttp import web

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

bot = Bot(token=TOKEN)
dp = Dispatcher()
known_users = set()

async def health_check(request):
    return web.Response(text="I am alive")

@dp.message()
async def handle_messages(message: types.Message):
    # Бот запоминает всех, кто пишет в чат
    known_users.add(message.from_user.id)
    
    if message.text == "/start":
        await message.answer("Я в строю! Теперь я вижу всех и готов тегать через @all или @все.")
    
    # Реакция на призыв
    elif message.text and any(x in message.text.lower() for x in ["@all", "@все", "/all"]):
        if known_users:
            # Создаем скрытые упоминания (те самые "собаки")
            mentions = "".join([f'<a href="tg://user?id={uid}">\u200b</a>' for uid in known_users])
            # ВОТ ТУТ я добавил слово "Всем"
            await message.answer(f"📢 <b>Внимание всем!</b>{mentions}", parse_mode="HTML")
        else:
            await message.answer("Я пока никого не знаю. Напишите что-нибудь, чтобы я вас запомнил!")

async def main():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    
    print(f"Робот запущен на порту {PORT}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
