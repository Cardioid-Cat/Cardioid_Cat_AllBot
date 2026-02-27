# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл с зависимостями
COPY requirements.txt .

# Устанавливаем библиотеки
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы проекта (код бота и базу данных)
COPY . .

# Открываем порт для веб-сервера (нужно для Render)
EXPOSE 10000

# Команда для запуска бота
CMD ["python", "Cardioid_Cat_AllBot.py"]
