import asyncio
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot, Dispatcher, types
from aiohttp import web

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
# ID твоей группы
GROUP_ID = -1003801387499 

bot = Bot(token=TOKEN)
dp = Dispatcher()
known_users = set()

# Функция, которая будет отправлять напоминание
async def send_kv_reminder():
    try:
        await bot.send_message(GROUP_ID, "ВСЕ ИГРАЕМ КВ СЕГОДНЯ!")
    except Exception as e:
        print(f"Ошибка при отправке напоминания: {e}")

async def health_check(request):
    return web.Response(text="I am alive")

@dp.message()
async def handle_messages(message: types.Message):
    known_users.add(message.from_user.id)
    
    if message.text == "/start":
        await message.answer("Я в строю! Теперь я вижу всех и готов тегать через @all или @все.")
    
    elif message.text and any(x in message.text.lower() for x in ["@all", "@все", "/all"]):
        if known_users:
            mentions = "".join([f'<a href="tg://user?id={uid}">\u200b</a>' for uid in known_users])
            await message.answer(f"📢 <b>Внимание всем!</b>{mentions}", parse_mode="HTML")
        else:
            await message.answer("Я пока никого не знаю. Напишите что-нибудь, чтобы я вас запомнил!")

async def main():
    # Настройка планировщика
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    # Добавляем задачу: чт, пт, сб, вс в 21:00
    scheduler.add_job(
        send_kv_reminder, 
        'cron', 
        day_of_week='thu,fri,sat,sun', 
        hour=21, 
        minute=0
    )
    scheduler.start() # Запускаем планировщик

    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    
    print(f"Робот запущен на порту {PORT} с планировщиком КВ")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
