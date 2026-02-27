import asyncio
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot, Dispatcher, types
from aiohttp import web

# Настройки из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
# ID твоей группы
GROUP_ID = -1003801387499 

bot = Bot(token=TOKEN)
dp = Dispatcher()
# Множество для хранения ID пользователей, чтобы тегать их через @all
known_users = set()

# Функция для автоматической рассылки
async def send_kv_reminder():
    try:
        if known_users:
            # Создаем скрытые упоминания (invisible tags)
            mentions = "".join([f'<a href="tg://user?id={uid}">\u200b</a>' for uid in known_users])
            text = f"📢 <b>@all ВСЕ ИГРАЕМ КВ СЕГОДНЯ!</b>{mentions}"
            await bot.send_message(GROUP_ID, text, parse_mode="HTML")
        else:
            # Если бот еще никого не запомнил после перезагрузки
            await bot.send_message(GROUP_ID, "@all ВСЕ ИГРАЕМ КВ СЕГОДНЯ!")
        print(f" Напоминание отправлено в {datetime.now()}")
    except Exception as e:
        print(f"Ошибка при отправке напоминания: {e}")

async def health_check(request):
    return web.Response(text="I am alive")

@dp.message()
async def handle_messages(message: types.Message):
    # Бот запоминает ID всех, кто пишет в чат, чтобы потом их тегнуть
    if message.from_user and not message.from_user.is_bot:
        known_users.add(message.from_user.id)
    
    if message.text == "/start":
        await message.answer("Я в строю! Теперь я вижу всех и готов тегать через @all или по расписанию.")
    
    # Ручной вызов тега всеми участниками
    elif message.text and any(x in message.text.lower() for x in ["@all", "@все", "/all"]):
        if known_users:
            mentions = "".join([f'<a href="tg://user?id={uid}">\u200b</a>' for uid in known_users])
            await message.answer(f"📢 <b>Внимание всем!</b>{mentions}", parse_mode="HTML")
        else:
            await message.answer("Я пока никого не знаю. Напишите что-нибудь, чтобы я вас запомнил!")

async def main():
    # Настройка планировщика (РФ/МСК часовой пояс)
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    
    # Добавляем задачу: чт, пт, сб, вс в 21:00
    scheduler.add_job(
        send_kv_reminder, 
        'cron', 
        day_of_week='thu,fri,sat,sun', 
        hour=21, 
        minute=0
    )
    scheduler.start()

    # Настройка веб-сервера для Health Check (нужно для Render/Railway)
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    
    print(f"Бот запущен. Напоминания настроены на ЧТ-ВС 21:00 МСК.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")
