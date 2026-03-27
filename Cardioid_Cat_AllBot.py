import asyncio, os
from aiogram import Bot, Dispatcher, types, F
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Токен и порт из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

# Твой новый ID группы
TARGET_GROUP_ID = -1003801387499

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- 1. ФУНКЦИЯ ДЛЯ УВЕДОМЛЕНИЙ ПО РАСПИСАНИЮ ---
async def send_kv_reminder():
    try:
        await bot.send_message(
            chat_id=TARGET_GROUP_ID,
            text="📢 <b>Внимание всем!</b> Сегодня играем КВ!",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка отправки по расписанию: {e}")

# --- 2. ОБРАБОТЧИК РУЧНОГО ВЫЗОВА (@все / @all) ---
@dp.message(F.text.in_(["@все", "@all"]))
async def call_all(m: types.Message):
    await m.answer("📢 <b>Внимание всем!</b> ⚡️", parse_mode="HTML")

# --- 3. ЗАПУСК БОТА И СЕРВЕРА ---
async def main():
    # Настройка планировщика. Укажи свой часовой пояс (сейчас стоит Москва)
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    
    # Расписание: четверг (thu), пятница (fri), суббота (sat), воскресенье (sun) в 22:00
    scheduler.add_job(
        send_kv_reminder, 
        trigger='cron', 
        day_of_week='thu,fri,sat,sun', 
        hour=22, 
        minute=0
    )
    scheduler.start()

    # Заглушка сервера, чтобы облачный хостинг не «убил» бота
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    
    # Запуск приема сообщений
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
