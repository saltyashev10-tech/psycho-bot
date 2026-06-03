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

# ============ КЛАВИАТУРА ============
main_keyboard = [
    ['🧘 Медитация', '📝 Упражнение'],
    ['💬 Поддержка', '📓 Дневник'],
    ['🆘 Экстренная помощь', 'ℹ️ О боте']
]

# ============ КОНТЕНТ ============
MEDITATIONS = {
    "breathing": """
🧘 **Дыхательная техника "4-7-8"**

1. Сядьте удобно, выпрямите спину
2. Сделайте глубокий вдох через нос на **4 счета**
3. Задержите дыхание на **7 счетов**
4. Медленно выдохните через рот на **8 счетов**
5. Повторите **4-8 раз**

✨ Эта техника помогает успокоиться и снять тревогу.
""",
    "body_scan": """
🧘 **Сканирование тела** (5 минут)

1. Закройте глаза и сделайте 3 глубоких вдоха
2. Направьте внимание на **ступни** — ощутите тепло или прохладу
3. Переместитесь к **голеням, коленям, бёдрам**
4. Затем **живот, грудь, спину**
5. Плечи, **руки, кисти**
6. **Шея, лицо, макушка**

Просто замечайте ощущения без оценки.
"""
}

EXERCISES = {
    "gratitude": """
📝 **Упражнение "Три благодарности"**

Напишите прямо сейчас (можно мысленно):
1. За что я благодарен(на) себе сегодня?
2. За что я благодарен(на) другому человеку?
3. За что я благодарен(на) миру/жизни?

✨ Исследования показывают: практика благодарности повышает уровень счастья.
""",
    "grounding": """
📝 **Техника "5-4-3-2-1"**

Назовите (про себя или вслух):

👁️ **5 вещей**, которые вы видите
👂 **4 звука**, которые вы слышите
🖐️ **3 вещи**, которые вы чувствуете кожей
👃 **2 запаха**, которые вы ощущаете
👅 **1 вкус**, который вы чувствуете

Это упражнение помогает при тревоге и панике.
"""
}

SUPPORT_MESSAGES = [
    "✨ Вы уже сделали большой шаг, обратившись за поддержкой. Это проявление силы!",
    "💚 Ваши чувства важны и имеют значение. Спасибо, что делитесь ими.",
    "🌟 Никто не обязан быть идеальным. Позвольте себе быть человеком с разными эмоциями.",
    "🌸 Помните: трудные времена не длятся вечно.",
    "💙 Вы не один. Многие люди проходят через похожие переживания.",
]

# ============ ОБРАБОТЧИКИ ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🙏 Привет, {user.first_name}!\n\n"
        f"Я бот психологической поддержки.\n\n"
        f"**Выберите, что вам нужно:**",
        reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def handle_meditation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['🌬️ Дыхание 4-7-8'],
        ['🧘 Сканирование тела'],
        ['🔙 Главное меню']
    ]
    await update.message.reply_text(
        "🧘 **Выберите практику:**",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def handle_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['🙏 Три благодарности'],
        ['🌍 Заземление 5-4-3-2-1'],
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

async def handle_diary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['diary_mode'] = True
    await update.message.reply_text(
        "📓 **Дневник настроения**\n\n"
        "Напишите, что вы чувствуете сейчас...\n"
        "Чтобы выйти из режима дневника, отправьте /cancel",
        parse_mode="Markdown"
    )

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

Этот бот помогает:
• справляться с тревогой и стрессом
• развивать навыки саморегуляции
• вести дневник настроения

**Важно:** Я не заменяю профессионального психолога.
"""
    await update.message.reply_text(about_text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('diary_mode'):
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
    
    # Режим дневника
    if context.user_data.get('diary_mode'):
        await update.message.reply_text("✅ Запись сохранена в дневнике. Продолжайте или отправьте /cancel")
        return
    
    # Меню выбора медитаций
    if text == "🌬️ Дыхание 4-7-8":
        await update.message.reply_text(MEDITATIONS["breathing"])
    elif text == "🧘 Сканирование тела":
        await update.message.reply_text(MEDITATIONS["body_scan"])
    
    # Меню выбора упражнений
    elif text == "🙏 Три благодарности":
        await update.message.reply_text(EXERCISES["gratitude"])
    elif text == "🌍 Заземление 5-4-3-2-1":
        await update.message.reply_text(EXERCISES["grounding"])
    
    # Главные кнопки
    elif text == "🧘 Медитация":
        await handle_meditation(update, context)
    elif text == "📝 Упражнение":
        await handle_exercise(update, context)
    elif text == "💬 Поддержка":
        await handle_support(update, context)
    elif text == "📓 Дневник":
        await handle_diary(update, context)
    elif text == "🆘 Экстренная помощь":
        await handle_emergency(update, context)
    elif text == "ℹ️ О боте":
        await handle_about(update, context)
    elif text == "🔙 Главное меню":
        await start(update, context)
    else:
        await update.message.reply_text(
            "Используйте кнопки меню для навигации.",
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )

# ============ ЗАПУСК ============
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
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ Бот психологической поддержки запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
