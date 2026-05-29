import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, filters

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask приложение
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Psycho Bot is running on Render!"

@flask_app.route('/env')
def show_env():
    """Тестовый эндпоинт для проверки переменных окружения"""
    env_vars = {
        'TELEGRAM_BOT_TOKEN': 'SET' if os.getenv('TELEGRAM_BOT_TOKEN') else 'NOT SET',
        'PORT': os.getenv('PORT', 'default'),
        'PYTHON_VERSION': os.getenv('PYTHON_VERSION', 'not set')
    }
    return env_vars

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# Команды бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Бот успешно запущен и работает!\n\n"
        "Я бот психологической поддержки. Я работаю 24/7 на Render.com!"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token_status = "✅ установлен" if os.getenv('TELEGRAM_BOT_TOKEN') else "❌ не найден"
    await update.message.reply_text(
        f"📊 Статус бота:\n"
        f"• Работает: ✅\n"
        f"• Токен: {token_status}\n"
        f"• Версия Python: {os.getenv('PYTHON_VERSION', '3.11.0')}"
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Вы написали: {update.message.text}")

def main():
    # ДИАГНОСТИКА: выводим все переменные окружения
    logger.info("=== ДИАГНОСТИКА ОКРУЖЕНИЯ ===")
    logger.info(f"Все переменные: {list(os.environ.keys())}")
    
    # Пробуем получить токен разными способами
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    token_alt = os.getenv("BOT_TOKEN")
    token_telegram = os.getenv("TELEGRAM_TOKEN")
    
    logger.info(f"TELEGRAM_BOT_TOKEN: {'НАЙДЕН' if token else 'НЕ НАЙДЕН'}")
    logger.info(f"BOT_TOKEN: {'НАЙДЕН' if token_alt else 'НЕ НАЙДЕН'}")
    logger.info(f"TELEGRAM_TOKEN: {'НАЙДЕН' if token_telegram else 'НЕ НАЙДЕН'}")
    
    # Если токен не найден, используем любой из альтернативных
    final_token = "8516115766:AAFhchBI9paY9KMDeT9WppKoEXshWtt67qE"
    
    if not final_token:
        logger.error("❌ Токен не найден ни в одной из переменных!")
        logger.error("Проверьте настройки Environment Variables в Render")
        logger.info("Продолжаем работу только веб-сервера для диагностики...")
        # Запускаем только Flask для диагностики
        run_flask()
        return
    
    logger.info(f"✅ Токен найден, длина: {len(final_token)}")
    
    # Запускаем Flask в фоне
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("🌐 Веб-сервер запущен")
    
    # Запускаем Telegram бота
    logger.info("🤖 Запуск Telegram бота...")
    telegram_app = Application.builder().token(final_token).build()
    
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("status", status))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    logger.info("✅ Бот готов к работе! Отправьте /start в Telegram")
    telegram_app.run_polling()

if __name__ == "__main__":
    main()
