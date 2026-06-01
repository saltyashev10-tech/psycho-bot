import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import random

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask приложение для Render
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Psycho Bot is running on Render!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# Клавиатура
main_keyboard = [
    ['🧘 Медитация', '📝 Упражнение'],
    ['💬 Поддержка', '📓 Дневник'],
    ['🆘 Экстренная помощь', 'ℹ️ О боте']
]

# Контент (сокращён для ясности)
SUPPORT_MESSAGES = [
    "✨ Вы уже сделали большой шаг!",
    "💚 Ваши чувства важны.",
    "🌟 Позвольте себе быть человеком."
]

# Обработчики
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🙏 Привет, {user.first_name}!\n\nЯ бот психологической поддержки.",
        reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🧘 Медитация":
        await update.message.reply_text("Выберите практику:\n1. Дыхание 4-7-8\n2. Сканирование тела")
    elif text == "💬 Поддержка":
        await update.message.reply_text(random.choice(SUPPORT_MESSAGES))
    elif text == "📓 Дневник":
        await update.message.reply_text("Напишите свои мысли. Функция в разработке.")
    elif text == "🆘 Экстренная помощь":
        await update.message.reply_text("📞 Телефон доверия: 8-800-2000-122")
    elif text == "ℹ️ О боте":
        await update.message.reply_text("Бот для психологической поддержки.")
    else:
        await update.message.reply_text("Используйте кнопки меню.")

# Запуск
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        logger.error("Токен не найден!")
        return

    # Запускаем Flask
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Веб-сервер запущен")

    # Создаём приложение
    app = Application.builder().token(token).build()

    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
