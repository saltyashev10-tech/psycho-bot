import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from dotenv import load_dotenv
import os

# Мои модули
from database import Database
from deepseek_api import deepseek_client

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

# Инициализация базы данных
db = Database()

# Клавиатуры
main_menu = [
    ['🧠 Поговорить с ИИ', '📓 Дневник настроения'],
    ['🧘 Медитация', '🆘 Экстренная помощь'],
    ['ℹ️ О боте']
]

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Добавляем пользователя в базу
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот психологической поддержки. 
Вот что я могу:

🧠 **Поговорить с ИИ** - обсудить чувства и получить поддержку
📓 **Дневник настроения** - записывать мысли и эмоции
🧘 **Медитация** - короткие практики для расслабления
🆘 **Экстренная помощь** - контакты специалистов

*Важно:* Я не заменяю психотерапевта!
"""
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
    )

# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    
    if user_message == "🧠 Поговорить с ИИ":
        await update.message.reply_text(
            "Расскажите, что вас беспокоит. Я готов выслушать...",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True)
        )
        context.user_data['mode'] = 'ai_chat'
        
    elif user_message == "📓 Дневник настроения":
        await update.message.reply_text(
            "Напишите, что вы чувствуете сегодня. "
            "Я сохраню это в вашем личном дневнике.",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True)
        )
        context.user_data['mode'] = 'journal'
        
    elif user_message == "🧘 Медитация":
        await send_meditation(update)
        
    elif user_message == "🆘 Экстренная помощь":
        await emergency_help(update)
        
    elif user_message == "ℹ️ О боте":
        await about_bot(update)
        
    elif user_message == "⬅️ Назад":
        await update.message.reply_text(
            "Возвращаюсь в главное меню",
            reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
        )
        context.user_data['mode'] = None
        
    else:
        # Определяем режим работы
        mode = context.user_data.get('mode')
        
        if mode == 'ai_chat':
            await ai_chat_handler(update, user_message)
        elif mode == 'journal':
            await journal_handler(update, user_message)
        else:
            await update.message.reply_text(
                "Используйте кнопки меню для навигации",
                reply_markup=ReplyKeyboardMarkup(main_menu, resize_keyboard=True)
            )

# Обработчик диалога с ИИ
async def ai_chat_handler(update: Update, user_message: str):
    # Показываем, что бот "печатает"
    await update.message.chat.send_action(action="typing")
    
    # Получаем ответ от DeepSeek
    ai_response = await deepseek_client.get_response(user_message)
    
    if ai_response:
        await update.message.reply_text(ai_response)
        
        # Сохраняем в базу
        db.conn.execute('''
            INSERT INTO ai_conversations (user_id, user_message, ai_response, created_at)
            VALUES (?, ?, ?, datetime('now'))
        ''', (update.effective_user.id, user_message, ai_response))
        db.conn.commit()
    else:
        await update.message.reply_text(
            "Извините, не могу получить ответ. "
            "Попробуйте позже или используйте другие функции бота."
        )

# Обработчик дневника
async def journal_handler(update: Update, user_message: str):
    db.add_journal_entry(update.effective_user.id, user_message)
    await update.message.reply_text(
        "✅ Запись сохранена в вашем дневнике.\n"
        "Можете продолжать писать или вернуться в меню.",
        reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True)
    )

# Медитации
async def send_meditation(update: Update):
    meditation_text = """
🧘 **Короткая медитация на 3 минуты:**

1. Сядьте удобно, закройте глаза
2. Сосредоточьтесь на дыхании
3. На вдохе говорите мысленно "вдох"
4. На выдохе - "выдох"
5. Если мысли отвлекают - мягко возвращайтесь к дыханию
6. Продолжайте 3 минуты

Заведите таймер и начинайте...
"""
    await update.message.reply_text(meditation_text)

# Экстренная помощь
async def emergency_help(update: Update):
    help_text = """
🆘 **Экстренная помощь:**

Если вам очень плохо:

*Телефоны доверия (круглосуточно, бесплатно):*
• 8-800-2000-122 - Единый телефон доверия
• 8-800-333-44-34 - Психологическая помощь
• 112 - Единый номер экстренных служб

*Техника "Заземление":*
1. Назовите 5 предметов, которые видите
2. 4 звука, которые слышите
3. 3 вещи, которые чувствуете (текстуры)
4. 2 запаха, которые ощущаете
5. 1 вкус (можно вспомнить)
"""
    await update.message.reply_text(help_text)

# О боте
async def about_bot(update: Update):
    about_text = """
ℹ️ **О боте:**

Этот бот создан для психологической поддержки.

*Что он делает:*
• Предоставляет эмоциональную поддержку через ИИ
• Помогает вести дневник настроения
• Предлагает медитации и техники релаксации

*Чего он НЕ делает:*
• Не ставит диагнозы
• Не заменяет психотерапевта
• Не работает в кризисных ситуациях

*Технологии:*
• Python + python-telegram-bot
• DeepSeek AI для диалогов
• SQLite для хранения данных
"""
    await update.message.reply_text(about_text)

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📋 **Доступные команды:**

/start - Начать работу
/help - Эта справка
/emergency - Экстренные контакты
/journal - Быстрая запись в дневник

Используйте кнопки меню для навигации.
"""
    await update.message.reply_text(help_text)

# Основная функция
def main():
    # Получаем токен из .env
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not TOKEN:
        logger.error("Токен не найден! Проверьте файл .env")
        return
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("emergency", emergency_help))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    logger.info("Бот запускается...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()