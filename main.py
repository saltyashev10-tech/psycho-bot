import os
import logging
import asyncio
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Настройка логирования (это поможет нам видеть ошибки) ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flask-приложение для того, чтобы Render не "усыпил" бота ---
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Psycho Bot is running!"

def run_flask():
    """Запускает веб-сервер в фоновом потоке"""
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# --- Логика вашего Telegram-бота ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветственное сообщение"""
    await update.message.reply_text(
        "Привет! Я бот психологической поддержки. Я работаю 24/7 на Render!"
    )

def main():
    """Главная функция для запуска бота"""
    # 1. Получаем токен из переменной окружения
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not TELEGRAM_TOKEN:
        logger.error("FATAL: Переменная окружения TELEGRAM_BOT_TOKEN не найдена!")
        return

    # 2. Запускаем Flask в отдельном потоке
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Веб-сервер для health check запущен.")

    # 3. Создаем и запускаем Telegram-бота
    logger.info("Запуск Telegram-бота...")
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    
    # Эта команда запускает бесконечный цикл получения обновлений от Telegram
    telegram_app.run_polling()

if __name__ == "__main__":
    main()
