import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flask-приложение для health checks ---
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Psycho Bot is running!"

def run_flask():
    """Запускает веб-сервер в фоновом потоке"""
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# --- Команды Telegram-бота ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветственное сообщение"""
    await update.message.reply_text(
        "Привет! Я бот психологической поддержки. Я работаю 24/7 на Render!\n\n"
        "Отправь мне любое сообщение, и я отвечу."
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отвечает эхом на любое текстовое сообщение"""
    user_message = update.message.text
    await update.message.reply_text(f"Ты написал: {user_message}")

# --- Запуск бота ---
def main():
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not TELEGRAM_TOKEN:
        logger.error("FATAL: Переменная TELEGRAM_BOT_TOKEN не найдена!")
        return

    # Запускаем Flask в фоновом потоке
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Веб-сервер для health check запущен.")

    # Создаем и запускаем Telegram-бота
    logger.info("Запуск Telegram-бота...")
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Запускаем polling (бесконечный цикл)
    telegram_app.run_polling()

if __name__ == "__main__":
    main()
