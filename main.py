import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import random
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask приложение для Render
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "Psycho Bot is running on Render!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port)

# ============ БАЗА ДАННЫХ ДНЕВНИКА (простая) ============
user_journals = {}

# ============ КЛАВИАТУРА ============
main_keyboard = [
    ['🧘 Медитация', '📝 Упражнение'],
    ['💬 Поддержка', '📓 Дневник'],
    ['🆘 Экстренная помощь', 'ℹ️ О боте']
]

# ============ ТЕХНИКИ И ПРАКТИКИ ============
MEDITATIONS = {
    "дыхание": """
🧘 **Дыхательная техника "4-7-8"**

1. Сядьте удобно, выпрямите спину
2. Сделайте глубокий вдох через нос на **4 счета**
3. Задержите дыхание на **7 счетов**
4. Медленно выдохните через рот на **8 счетов**
5. Повторите **4-8 раз**

✨ Эта техника помогает успокоиться и снять тревогу.
""",
    "сканирование": """
🧘 **Сканирование тела** (5 минут)

1. Закройте глаза и сделайте 3 глубоких вдоха
2. Направьте внимание на **ступни** — ощутите тепло или прохладу
3. Переместитесь к **голеням, коленям, бёдрам**
4. Затем **живот, грудь, спину**
5. Плечи, **руки, кисти**
6. **Шея, лицо, макушка**

Просто замечайте ощущения без оценки.
""",
    "осознанность": """
🧘 **Минута осознанности**

Прямо сейчас, не закрывая глаз:

• Назовите **3 вещи**, которые вы видите вокруг
• Назовите **2 звука**, которые вы слышите
• Ощутите **1 тактильное ощущение** (прикосновение одежды, стула)

Это упражнение возвращает вас в настоящий момент.
"""
}

EXERCISES = {
    "благодарность": """
📝 **Упражнение "Три благодарности"**

Напишите прямо сейчас (можно мысленно):
1. За что я благодарен(на) себе сегодня?
2. За что я благодарен(на) другому человеку?
3. За что я благодарен(на) миру/жизни?

✨ Исследования показывают: практика благодарности повышает уровень счастья на 25%.
""",
    "переоценка": """
📝 **Когнитивное переформулирование**

Подумайте о ситуации, которая вас тревожит, и ответьте:

❌ **Мысль-автомат:** "У меня ничего не получится"
✅ **Реалистичная мысль:** "У меня уже есть опыт, я справлялся(лась) раньше"

❌ **Мысль-автомат:** "Все на меня смотрят и осуждают"
✅ **Реалистичная мысль:** "Люди заняты собой, у каждого свои заботы"

Перепишите свои негативные мысли.
""",
    "заземление": """
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
    "✨ Вы уже сделали большой шаг, обратившись за поддержкой. Это проявление силы, а не слабости.",
    "💚 Ваши чувства важны и имеют значение. Спасибо, что делитесь ими.",
    "🌟 Никто не обязан быть идеальным. Позвольте себе быть человеком с разными эмоциями.",
    "🌸 Помните: трудные времена не длятся вечно, но трудные люди становятся сильнее.",
    "💙 Вы не один. Многие люди проходят через похожие переживания.",
]

# ============ ОБРАБОТЧИКИ КОМАНД ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет главное меню"""
    user = update.effective_user
    
    await update.message.reply_text(
        f"🙏 Привет, {user.first_name}!\n\n"
        f"Я бот психологической поддержки. Я здесь, чтобы помочь:\n"
        f"• справиться с тревогой и стрессом\n"
        f"• восстановить эмоциональное равновесие\n"
        f"• найти внутренние ресурсы\n\n"
        f"**Выберите, что вам нужно:**",
        reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def meditation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет выбор медитаций"""
    keyboard = [
        [InlineKeyboardButton("🌬️ Дыхательная техника", callback_data="med_breathing")],
        [InlineKeyboardButton("🧘 Сканирование тела", callback_data="med_scan")],
        [InlineKeyboardButton("🎯 Минута осознанности", callback_data="med_mindful")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
    ]
    await update.message.reply_text(
        "🧘 **Практики осознанности:**\n\n"
        "Выберите технику, которая подходит вам сейчас:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def exercise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет выбор упражнений"""
    keyboard = [
        [InlineKeyboardButton("🙏 Три благодарности", callback_data="exc_gratitude")],
        [InlineKeyboardButton("🔄 Переоценка мыслей", callback_data="exc_reframe")],
        [InlineKeyboardButton("🌍 Заземление 5-4-3-2-1", callback_data="exc_grounding")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
    ]
    await update.message.reply_text(
        "📝 **Терапевтические упражнения:**\n\n"
        "Выберите упражнение — это займёт 3-5 минут:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет сообщение поддержки"""
    random_message = random.choice(SUPPORT_MESSAGES)
    keyboard = [
        [InlineKeyboardButton("🙏 Ещё одно", callback_data="another_support")],
        [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu")]
    ]
    await update.message.reply_text(
        f"{random_message}\n\n"
        f"Хотите ещё одно ободряющее сообщение?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def diary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает запись в дневник"""
    context.user_data['diary_mode'] = True
    await update.message.reply_text(
        "📓 **Дневник настроения**\n\n"
        "Напишите, что вы чувствуете сейчас...\n"
        "Это может быть:\n"
        "• ваше настроение\n"
        "• мысли, которые беспокоят\n"
        "• то, за что вы благодарны\n\n"
        "Просто напишите сообщение — и оно сохранится.\n"
        "Чтобы выйти из режима дневника, отправьте /cancel",
        parse_mode="Markdown"
    )

async def emergency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экстренная помощь"""
    emergency_text = """
🆘 **Если вам нужна помощь прямо сейчас:**

📞 **Горячие линии (Россия, 24/7):**

• **8-800-2000-122** — Единый телефон доверия
• **8-800-333-44-34** — Психологическая помощь
• **112** — Экстренные службы

🌐 **Онлайн-помощь:**
• https://pomogut.ru — бесплатная психологическая помощь
• https://psi.mos.ru — служба психологической помощи

💙 **Помните:** обратиться за помощью — это правильно и ответственно.
"""
    await update.message.reply_text(emergency_text)

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """О боте"""
    about_text = """
ℹ️ **О боте психологической поддержки**

Этот бот создан, чтобы помочь вам:
• справляться с тревогой и стрессом
• развивать навыки саморегуляции
• вести дневник настроения

**Важно:** Я не заменяю профессионального психолога или психотерапевта. Если вам тяжело — обратитесь к специалисту.

**Разработчик:** Проект создан с заботой о ментальном здоровье.
"""
    await update.message.reply_text(about_text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущего режима"""
    if context.user_data.get('diary_mode'):
        context.user_data['diary_mode'] = False
        await update.message.reply_text(
            "Режим дневника завершён. Возвращаюсь в главное меню.",
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )
    else:
        await update.message.reply_text("Нет активных режимов для отмены.")

# ============ ОБРАБОТКА INLINE-КНОПОК ============

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия на inline-кнопки"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "back_to_menu":
        await query.edit_message_text(
            "🏠 **Главное меню**\n\nВыберите нужный раздел:",
            parse_mode="Markdown"
        )
        await query.message.reply_text(
            "Используйте кнопки ниже:",
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )
    
    elif data == "another_support":
        random_message = random.choice(SUPPORT_MESSAGES)
        await query.edit_message_text(
            f"{random_message}\n\n"
            f"Хотите ещё одно сообщение?",
            reply_markup=query.message.reply_markup
        )
    
    elif data == "med_breathing":
        await query.edit_message_text(MEDITATIONS["дыхание"], parse_mode="Markdown")
    elif data == "med_scan":
        await query.edit_message_text(MEDITATIONS["сканирование"], parse_mode="Markdown")
    elif data == "med_mindful":
        await query.edit_message_text(MEDITATIONS["осознанность"], parse_mode="Markdown")
    
    elif data == "exc_gratitude":
        await query.edit_message_text(EXERCISES["благодарность"], parse_mode="Markdown")
    elif data == "exc_reframe":
        await query.edit_message_text(EXERCISES["переоценка"], parse_mode="Markdown")
    elif data == "exc_grounding":
        await query.edit_message_text(EXERCISES["заземление"], parse_mode="Markdown")

# ============ ОБРАБОТКА СООБЩЕНИЙ ============

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения"""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Проверяем, в режиме ли дневника пользователь
    if context.user_data.get('diary_mode'):
        # Сохраняем запись в дневнике
        if user_id not in user_journals:
            user_journals[user_id] = []
        user_journals[user_id].append(text)
        await update.message.reply_text(
            "✅ Запись сохранена в дневнике.\n\n"
            "Можете продолжать писать (каждая запись будет сохраняться) или отправьте /cancel чтобы выйти.",
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )
        return
    
    # Обработка кнопок меню
    if text == "🧘 Медитация":
        await meditation(update, context)
    elif text == "📝 Упражнение":
        await exercise(update, context)
    elif text == "💬 Поддержка":
        await support(update, context)
    elif text == "📓 Дневник":
        await diary(update, context)
    elif text == "🆘 Экстренная помощь":
        await emergency(update, context)
    elif text == "ℹ️ О боте":
        await about(update, context)
    else:
        # Обычный ответ, если не команда
        await update.message.reply_text(
            "Используйте кнопки меню для навигации.\n\n"
            "🧘 Медитация — практики осознанности\n"
            "📝 Упражнение — терапевтические техники\n"
            "💬 Поддержка — ободряющие сообщения\n"
            "📓 Дневник — сохранить мысли и чувства"
        )

# ============ ЗАПУСК БОТА ============

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        logger.error("Токен не найден!")
        return
    
    # Запускаем Flask
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Создаём приложение
    app = Application.builder().token(token).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    
    # Обработчик кнопок меню
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик inline-кнопок
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("✅ Бот психологической поддержки запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
