import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import random
import aiohttp
import asyncio
from database import Database

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = Database("psycho_bot.db")

# Flask приложение
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Psycho Bot is running on Render!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# Клавиатура
main_keyboard = [
    ['🤖 Поговорить с ИИ', '🧘 Медитация'],
    ['📝 Упражнение', '💬 Поддержка'],
    ['📓 Дневник', '📊 Статистика'],
    ['🆘 Помощь', 'ℹ️ О боте']
]

# Контент
MEDITATIONS = {
    "breathing": "🌬️ **Дыхательная техника 4-7-8**\n\n1. Вдох на 4 счета\n2. Задержка на 7 счетов\n3. Выдох на 8 счетов",
    "mindfulness": "🧘 **Медитация осознанности**\n\nСосредоточьтесь на дыхании, замечайте мысли без оценки.",
}

EXERCISES = {
    "gratitude": "🙏 **Три благодарности**\n\nНапишите, за что вы благодарны себе, другому человеку и миру.",
    "grounding": "🌍 **Заземление 5-4-3-2-1**\n\nНазовите: 5 вещей, 4 звука, 3 тактильных ощущения, 2 запаха, 1 вкус.",
}

SUPPORT_MESSAGES = [
    "✨ Вы уже сделали большой шаг!",
    "💚 Ваши чувства важны.",
    "🌟 Позвольте себе быть человеком.",
]

# Системный промпт для DeepSeek
SYSTEM_PROMPT = """
Ты — добрый психологический помощник.
Отвечай на русском, будь внимательным.
Не ставь диагнозов.
"""

async def ask_deepseek(user_message: str, conversation_history: list = None) -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        return random.choice([
            "Расскажите подробнее, я вас слушаю.",
            "Понимаю. Что вы чувствуете сейчас?"
        ])
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if conversation_history:
        for msg in conversation_history[-6:]:
            messages.append(msg)
    messages.append({"role": "user", "content": user_message})
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                timeout=30
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return "Извините, сервис временно недоступен. Попробуйте позже."
    except Exception as e:
        logger.error(f"DeepSeek error: {e}")
        return "Произошла ошибка. Давайте попробуем простое дыхательное упражнение."

user_conversations = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Сохраняем пользователя в базу
    db.add_user(user_id, user.username, user.first_name, user.last_name)
    db.update_last_active(user_id)
    
    await update.message.reply_text(
        f"🙏 Привет, {user.first_name}!\n\nЯ психологический помощник с ИИ.\nВыберите действие:",
        reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    )

async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    context.user_data['ai_mode'] = True
    await update.message.reply_text(
        "🤖 Режим диалога с ИИ\n\nРасскажите, что вас беспокоит.\nЧтобы выйти, отправьте /cancel"
    )

async def handle_ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('ai_mode'):
        return False
    
    user_id = update.effective_user.id
    user_message = update.message.text
    
    db.update_last_active(user_id)
    db.increment_stat(user_id, "total_messages")
    db.increment_stat(user_id, "ai_messages_count")
    
    await update.message.chat.send_action(action="typing")
    
    history = user_conversations.get(user_id, [])
    response = await ask_deepseek(user_message, history)
    
    # Сохраняем в историю и базу
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": response})
    user_conversations[user_id] = history[-20:]  # Храним последние 20 сообщений
    
    db.add_ai_message(user_id, "user", user_message)
    db.add_ai_message(user_id, "assistant", response)
    
    await update.message.reply_text(response)
    return True

async def handle_meditation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    db.increment_stat(user_id, "meditations_count")
    
    keyboard = [
        ['🌬️ Дыхание 4-7-8'],
        ['🧘 Осознанность'],
        ['🔙 Главное меню']
    ]
    await update.message.reply_text(
        "🧘 **Выберите медитацию:**",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def handle_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    db.increment_stat(user_id, "exercises_count")
    
    keyboard = [
        ['🙏 Три благодарности'],
        ['🌍 Заземление'],
        ['🔙 Главное меню']
    ]
    await update.message.reply_text(
        "📝 **Выберите упражнение:**",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def handle_diary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    context.user_data['diary_mode'] = True
    await update.message.reply_text(
        "📓 **Дневник**\n\nНапишите, что чувствуете. /cancel для выхода",
        parse_mode="Markdown"
    )

async def handle_diary_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('diary_mode'):
        return False
    
    user_id = update.effective_user.id
    entry = update.message.text
    
    db.add_diary_entry(user_id, entry)
    db.increment_stat(user_id, "total_messages")
    
    await update.message.reply_text("✅ Запись сохранена в дневнике!")
    return True

async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    
    stats = db.get_stats(user_id)
    if stats:
        stats_text = f"""
📊 **Ваша статистика:**

🧘 Медитаций: {stats['meditations_count']}
📝 Упражнений: {stats['exercises_count']}
💬 Сообщений ИИ: {stats['ai_messages_count']}
📨 Всего сообщений: {stats['total_messages']}

🌟 Продолжайте заботиться о себе!
"""
        await update.message.reply_text(stats_text, parse_mode="Markdown")
    else:
        await update.message.reply_text("Статистика пока пуста. Начните практиковать!")

async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    await update.message.reply_text(random.choice(SUPPORT_MESSAGES))

async def handle_emergency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 Телефон доверия: 8-800-2000-122 (24/7)\n112 — экстренные службы"
    )

async def handle_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Бот психологической поддержки с ИИ.\n"
        "Технологии: Python + DeepSeek + Render\n"
        "База данных: SQLite"
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('ai_mode'):
        context.user_data['ai_mode'] = False
        await update.message.reply_text("Режим ИИ завершён.", reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True))
    elif context.user_data.get('diary_mode'):
        context.user_data['diary_mode'] = False
        await update.message.reply_text("Режим дневника завершён.", reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True))
    else:
        await update.message.reply_text("Нет активных режимов для отмены.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if context.user_data.get('ai_mode'):
        await handle_ai_message(update, context)
        return
    
    if context.user_data.get('diary_mode'):
        await handle_diary_message(update, context)
        return
    
    if text == "🤖 Поговорить с ИИ":
        await handle_ai_chat(update, context)
    elif text == "🧘 Медитация":
        await handle_meditation(update, context)
    elif text == "📝 Упражнение":
        await handle_exercise(update, context)
    elif text == "📓 Дневник":
        await handle_diary(update, context)
    elif text == "📊 Статистика":
        await handle_stats(update, context)
    elif text == "💬 Поддержка":
        await handle_support(update, context)
    elif text == "🆘 Помощь":
        await handle_emergency(update, context)
    elif text == "ℹ️ О боте":
        await handle_about(update, context)
    elif text == "🔙 Главное меню":
        await start(update, context)
    elif text == "🌬️ Дыхание 4-7-8":
        await update.message.reply_text(MEDITATIONS["breathing"])
    elif text == "🧘 Осознанность":
        await update.message.reply_text(MEDITATIONS["mindfulness"])
    elif text == "🙏 Три благодарности":
        await update.message.reply_text(EXERCISES["gratitude"])
    elif text == "🌍 Заземление":
        await update.message.reply_text(EXERCISES["grounding"])
    else:
        await update.message.reply_text("Используйте кнопки меню.")

def main():
    token = "8516115766:AAFhchBI9paY9KMDeT9WppKoEXshWtt67qE"
    
    if not token:
        logger.error("Токен не найден!")
        return
    
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Веб-сервер запущен")
    
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ Бот с ИИ и базой данных запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
