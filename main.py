import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import random
import aiohttp
import asyncio

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

# ============ КЛАВИАТУРА ============
main_keyboard = [
    ['🤖 Поговорить с ИИ', '🧘 Медитация'],
    ['📝 Упражнение', '💬 Поддержка'],
    ['📓 Дневник', '🆘 Помощь'],
    ['ℹ️ О боте']
]

# ============ КОНТЕНТ (оставляем для резерва) ============
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

# ============ ИНТЕГРАЦИЯ С DEEPSEEK ============
# Системный промпт — задаёт "личность" бота
# ============ ИНТЕГРАЦИЯ С DEEPSEEK ============
# Системный промпт — задаёт "личность" бота
SYSTEM_PROMPT = """
Ты — добрый и эмпатичный психологический помощник по имени ПсихоBot.

Твои правила:
1. Всегда отвечай на русском языке
2. Будь внимательным и поддерживающим
3. Не ставь диагнозов и не давай медицинских советов
4. Если пользователь говорит о суицидальных мыслях — сразу предложи обратиться к специалисту (телефон доверия: 8-800-2000-122)
5. Используй простой, понятный язык
6. Задавай уточняющие вопросы, чтобы лучше понять состояние пользователя
7. Предлагай простые техники (дыхание, заземление) если видишь тревогу

Примеры ответов:
- "Я слышу, что тебе сейчас тяжело. Расскажи подробнее, что происходит?"
- "Понимаю твои чувства. Это нормально — испытывать грусть/тревогу/злость. Давай попробуем дыхательное упражнение?"
- "Спасибо, что поделился. Как ты думаешь, что могло бы тебе помочь прямо сейчас?"
"""

async def ask_deepseek(user_message: str, conversation_history: list = None) -> str:
    """Отправляет запрос к DeepSeek API и возвращает ответ"""
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    # Если ключа нет — возвращаем заглушку
    if not api_key:
        logger.warning("DEEPSEEK_API_KEY не найден, использую заглушку")
        return random.choice([
            "Расскажите подробнее, я вас слушаю.",
            "Понимаю. Что вы чувствуете сейчас?",
            "Спасибо, что делитесь. Как я могу помочь?"
        ])
    
    # Формируем историю диалога
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if conversation_history:
        messages.extend(conversation_history[-10:])  # Последние 10 сообщений для контекста
    
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
                    error_text = await response.text()
                    logger.error(f"DeepSeek API ошибка: {response.status} - {error_text}")
                    return "Извините, сейчас не могу ответить. Попробуйте позже или выберите другую функцию."
                    
    except asyncio.TimeoutError:
        logger.error("DeepSeek API timeout")
        return "Сервис временно недоступен. Попробуйте ещё раз через минуту."
    except Exception as e:
        logger.error(f"DeepSeek API exception: {e}")
        return "Произошла ошибка. Давайте попробуем простое упражнение: сделайте 3 глубоких вдоха."

# ============ ОБРАБОТЧИКИ ============
# Хранилище истории диалогов (в памяти, при перезапуске сбрасывается)
user_conversations = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Инициализируем историю пользователя
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    await update.message.reply_text(
        f"🙏 Привет, {user.first_name}!\n\n"
        f"Я психологический помощник с ИИ. Я могу:\n"
        f"🤖 **Поговорить с ИИ** — обсудить чувства и получить поддержку\n"
        f"🧘 **Медитация** — короткие практики для расслабления\n"
        f"📝 **Упражнение** — психологические техники\n"
        f"💬 **Поддержка** — ободряющие сообщения\n"
        f"📓 **Дневник** — записать мысли\n\n"
        f"**Выберите, что вам нужно:**",
        reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка диалога с ИИ"""
    user_id = update.effective_user.id
    
    # Инициализируем историю, если её нет
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    # Ждём следующее сообщение
    await update.message.reply_text(
        "🤖 **Режим диалога с ИИ**\n\n"
        "Расскажите, что вас беспокоит. Я внимательно выслушаю и постараюсь помочь.\n\n"
        "Чтобы выйти из режима, отправьте /cancel",
        parse_mode="Markdown"
    )
    context.user_data['ai_mode'] = True

async def handle_ai_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает сообщение в режиме ИИ"""
    if not context.user_data.get('ai_mode'):
        return False
    
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Показываем, что бот "печатает"
    await update.message.chat.send_action(action="typing")
    
    # Получаем историю пользователя
    history = user_conversations.get(user_id, [])
    
    # Запрашиваем ответ у DeepSeek
    response = await ask_deepseek(user_message, history)
    
    # Сохраняем в историю
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": response})
    user_conversations[user_id] = history
    
    # Отправляем ответ
    await update.message.reply_text(response)
    
    return True

async def handle_meditation(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = random.choice(SUPPORT_MESSAGES)
    await update.message.reply_text(message)

async def handle_emergency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    emergency_text = """
🆘 **Если вам нужна помощь прямо сейчас:**

📞 **Горячие линии (24/7):**
• **8-800-2000-122** — Единый телефон доверия
• **112** — Экстренные службы

💙 Помните: обратиться за помощью — это правильно.
"""
    await update.message.reply_text(emergency_text)

async def handle_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = """
ℹ️ **О боте психологической поддержки**

**Что умеет бот:**
• 🤖 **ИИ-помощник** — осмысленный диалог с нейросетью
• 🧘 **Медитации** — практики осознанности
• 📝 **Упражнения** — психологические техники
• 💬 **Поддержка** — ободряющие сообщения
• 📓 **Дневник** — сохранение мыслей

**Технологии:** Python + DeepSeek AI + Render + UptimeRobot

**Важно:** Я не заменяю профессионального психолога.
"""
    await update.message.reply_text(about_text)

async def handle_diary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['diary_mode'] = True
    await update.message.reply_text(
        "📓 **Дневник настроения**\n\n"
        "Напишите, что вы чувствуете сейчас...\n"
        "Чтобы выйти, отправьте /cancel",
        parse_mode="Markdown"
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('ai_mode'):
        context.user_data['ai_mode'] = False
        await update.message.reply_text(
            "Режим ИИ завершён. Возвращаюсь в главное меню.",
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )
    elif context.user_data.get('diary_mode'):
        context.user_data['diary_mode'] = False
        await update.message.reply_text(
            "Режим дневника завершён.",
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )
    else:
        await update.message.reply_text("Нет активных режимов для отмены.")

# ============ ГЛАВНЫЙ ОБРАБОТЧИК ============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    # Сначала проверяем режим ИИ (если активен)
    if context.user_data.get('ai_mode'):
        await handle_ai_message(update, context)
        return
    
    # Режим дневника
    if context.user_data.get('diary_mode'):
        await update.message.reply_text("✅ Запись сохранена в дневнике.")
        return
    
    # Обработка кнопок
    if text == "🤖 Поговорить с ИИ":
        await handle_ai_chat(update, context)
    elif text == "🧘 Медитация":
        await handle_meditation(update, context)
    elif text == "📝 Упражнение":
        await handle_exercise(update, context)
    elif text == "💬 Поддержка":
        await handle_support(update, context)
    elif text == "📓 Дневник":
        await handle_diary(update, context)
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
        await update.message.reply_text(
            "Используйте кнопки меню для навигации.\n\n"
            "🤖 **Поговорить с ИИ** — живой диалог с нейросетью\n"
            "🧘 **Медитация** — практики осознанности\n"
            "📝 **Упражнение** — психологические техники\n"
            "💬 **Поддержка** — ободряющие сообщения",
            parse_mode="Markdown"
        )

# ============ ЗАПУСК ============
def main():
    token = "8516115766:AAFhchBI9paY9KMDeT9WppKoEXshWtt67qE"
    
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
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ Бот с ИИ запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
