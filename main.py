import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import random
import json

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

# ============ РАСШИРЕННАЯ КЛАВИАТУРА ============
main_keyboard = [
    ['🧘 Медитации', '📝 Упражнения'],
    ['💬 Поддержка', '📓 Дневник'],
    ['🎵 Звуки природы', '🆘 Помощь'],
    ['📊 Статистика', 'ℹ️ О боте']
]

meditation_keyboard = [
    ['🌬️ Дыхание', '🧘 Осознанность'],
    ['💪 Снятие стресса', '😴 Перед сном'],
    ['🔙 Главное меню']
]

exercise_keyboard = [
    ['🙏 Благодарность', '🔄 Переоценка'],
    ['🌍 Заземление', '💪 Аффирмации'],
    ['📝 Дневник мыслей', '🔙 Главное меню']
]

# ============ РАСШИРЕННЫЕ МЕДИТАЦИИ ============
MEDITATIONS = {
    "breathing": """
🌬️ **Дыхательная техника "4-7-8"**

Эта техника помогает успокоиться за 1-2 минуты.

📋 **Инструкция:**
1. Сядьте удобно, выпрямите спину
2. Сделайте глубокий вдох через нос на **4 счета**
3. Задержите дыхание на **7 счетов**
4. Медленно выдохните через рот на **8 счетов**
5. Повторите **4-8 раз**

✨ **Эффект:** снижает тревогу, успокаивает нервную систему.
""",
    "mindfulness": """
🧘 **Медитация осознанности** (5 минут)

🎯 **Цель:** научиться быть в настоящем моменте.

📋 **Инструкция:**
1. Закройте глаза и сосредоточьтесь на дыхании
2. Замечайте каждую мысль, но не цепляйтесь за неё
3. Представьте мысли как облака — они приходят и уходят
4. Если отвлеклись — мягко вернитесь к дыханию
5. Откройте глаза и зафиксируйте ощущения

💡 **Совет:** Практикуйте ежедневно по 5-10 минут.
""",
    "stress_relief": """
💪 **Медитация для снятия стресса** (7 минут)

🎯 **Цель:** быстро снять физическое и эмоциональное напряжение.

📋 **Инструкция:**
1. Сядьте или лягте удобно
2. На вдохе напрягите всё тело на 5 секунд
3. На выдохе полностью расслабьтесь
4. Повторите 3 раза
5. Затем дышите спокойно, представляя, как стресс покидает тело

💡 **Когда применять:** после тяжёлого дня, перед важными событиями.
""",
    "sleep": """
😴 **Медитация перед сном** (10 минут)

🎯 **Цель:** подготовить ум и тело ко сну.

📋 **Инструкция:**
1. Лягте в кровать, выключите свет
2. Сосредоточьтесь на дыхании животом
3. На выдохе мысленно говорите «спокойствие»
4. Представьте тёплый свет, который расслабляет каждую часть тела
5. Если мысли отвлекают — не боритесь, просто наблюдайте

✨ **Эффект:** улучшает качество сна, снижает тревожность.
"""
}

# ============ РАСШИРЕННЫЕ УПРАЖНЕНИЯ ============
EXERCISES = {
    "gratitude": """
🙏 **Упражнение "Три благодарности"**

🎯 **Цель:** научиться замечать хорошее в жизни.

📋 **Инструкция:**
Напишите (можно мысленно) прямо сейчас:
1. За что я благодарен(на) **себе** сегодня?
2. За что я благодарен(на) **другому человеку**?
3. За что я благодарен(на) **миру/жизни**?

✨ **Исследования:** ежедневная практика благодарности повышает уровень счастья на 25%.
""",
    "grounding": """
🌍 **Техника "5-4-3-2-1"**

🎯 **Цель:** быстро вернуться в настоящий момент при тревоге или панике.

📋 **Инструкция:**
Назовите (про себя или вслух):

👁️ **5 вещей**, которые вы видите
👂 **4 звука**, которые вы слышите
🖐️ **3 вещи**, которые вы чувствуете кожей
👃 **2 запаха**, которые вы ощущаете
👅 **1 вкус**, который вы чувствуете

✨ **Эффект:** помогает при панических атаках и сильной тревоге.
""",
    "reframe": """
🔄 **Когнитивное переформулирование**

🎯 **Цель:** научиться менять негативные мысли на реалистичные.

📋 **Инструкция:**
Подумайте о ситуации, которая вас тревожит:

❌ **Мысль-автомат:** "У меня ничего не получится"
✅ **Реалистичная мысль:** "У меня уже есть опыт, я справлялся(лась) раньше"

❌ **Мысль-автомат:** "Все на меня смотрят и осуждают"
✅ **Реалистичная мысль:** "Люди заняты собой, у каждого свои заботы"

Теперь перепишите свои негативные мысли.
""",
    "affirmations": """
💪 **Утренние аффирмации**

🎯 **Цель:** настроиться на позитивный день.

📋 **Повторяйте каждое утро:**

🌟 Я принимаю себя таким(ой), какой(ая) я есть
🌟 У меня достаточно сил и ресурсов
🌟 Я разрешаю себе ошибаться и учиться
🌟 Я открыт(а) новым возможностям
🌟 Сегодня будет хороший день

💡 **Совет:** Повторяйте перед зеркалом или записывайте в дневник.
""",
    "thought_diary": """
📝 **Дневник мыслей** (КПТ-упражнение)

🎯 **Цель:** отслеживать связь между мыслями, эмоциями и поведением.

📋 **Ответьте на вопросы:**

1. **Ситуация:** Что произошло?
2. **Мысли:** Что я подумал(а) в тот момент?
3. **Эмоции:** Что я почувствовал(а) (оценка 1-10)?
4. **Действия:** Что я сделал(а)?
5. **Новая мысль:** Как можно подумать иначе?

💡 **Результат:** вы научитесь замечать и менять автоматические негативные мысли.
"""
}

# ============ ЗВУКИ ПРИРОДЫ ============
NATURE_SOUNDS = {
    "rain": "🌧️ Звук дождя: https://youtu.be/dQw4w9WgXcQ (замените на реальную ссылку)",
    "forest": "🌲 Звуки леса: https://youtu.be/dQw4w9WgXcQ",
    "ocean": "🌊 Океан: https://youtu.be/dQw4w9WgXcQ",
    "fire": "🔥 Костер: https://youtu.be/dQw4w9WgXcQ"
}

# ============ ПОДДЕРЖКА ============
SUPPORT_MESSAGES = [
    "✨ Вы уже сделали большой шаг, обратившись за поддержкой. Это проявление силы!",
    "💚 Ваши чувства важны и имеют значение. Спасибо, что делитесь ими.",
    "🌟 Никто не обязан быть идеальным. Позвольте себе быть человеком с разными эмоциями.",
    "🌸 Помните: трудные времена не длятся вечно.",
    "💙 Вы не один. Многие люди проходят через похожие переживания.",
    "🌱 Каждый день — это новый шанс начать заботиться о себе.",
    "🕊️ Вы делаете достаточно. Вы достаточно хороши.",
    "💪 Просить помощи — это не слабость, а мудрость.",
]

# Хранение статистики пользователей (в памяти, при перезапуске сбрасывается)
user_stats = {}

# ============ ОБРАБОТЧИКИ ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Инициализируем статистику
    if user_id not in user_stats:
        user_stats[user_id] = {"meditations": 0, "exercises": 0, "start_date": str(update.message.date)}
    
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

async def show_meditations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧘 **Выберите медитацию:**",
        reply_markup=ReplyKeyboardMarkup(meditation_keyboard, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def show_exercises(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 **Выберите упражнение:**",
        reply_markup=ReplyKeyboardMarkup(exercise_keyboard, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def show_nature_sounds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sounds_text = "🎵 **Звуки природы для релаксации:**\n\n"
    for key, value in NATURE_SOUNDS.items():
        sounds_text += f"• {value}\n"
    sounds_text += "\n💡 *Совет:* используйте наушники для лучшего эффекта."
    await update.message.reply_text(sounds_text, parse_mode="Markdown")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = user_stats.get(user_id, {"meditations": 0, "exercises": 0})
    
    stats_text = f"""
📊 **Ваша статистика:**

🧘 Медитаций выполнено: {stats.get('meditations', 0)}
📝 Упражнений выполнено: {stats.get('exercises', 0)}

🌟 Вы молодец! Продолжайте в том же духе!
"""
    await update.message.reply_text(stats_text, parse_mode="Markdown")

async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = random.choice(SUPPORT_MESSAGES)
    await update.message.reply_text(message)

async def handle_emergency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    emergency_text = """
🆘 **Если вам нужна помощь прямо сейчас:**

📞 **Горячие линии (24/7):**

• **8-800-2000-122** — Единый телефон доверия
• **112** — Экстренные службы

🌐 **Онлайн-помощь:**
• https://pomogut.ru — бесплатная психологическая помощь

💙 **Помните:** обратиться за помощью — это правильно и ответственно.
"""
    await update.message.reply_text(emergency_text)

async def handle_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = """
ℹ️ **О боте психологической поддержки**

**Что умеет бот:**
• 🧘 4 вида медитаций
• 📝 5 психологических упражнений
• 🎵 Звуки природы для релаксации
• 💬 Поддержка в трудную минуту
• 📓 Дневник настроения
• 📊 Статистика прогресса

**Важно:** Я не заменяю профессионального психолога. Если вам тяжело — обратитесь к специалисту.

**Разработчик:** Проект создан с заботой о ментальном здоровье.
"""
    await update.message.reply_text(about_text)

async def handle_diary(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    user_id = update.effective_user.id
    
    # Инициализация статистики
    if user_id not in user_stats:
        user_stats[user_id] = {"meditations": 0, "exercises": 0, "start_date": str(update.message.date)}
    
    # Режим дневника
    if context.user_data.get('diary_mode'):
        await update.message.reply_text("✅ Запись сохранена в дневнике.")
        return
    
    # ===== МЕДИТАЦИИ =====
    if text == "🧘 Медитации":
        await show_meditations(update, context)
    elif text == "🌬️ Дыхание":
        await update.message.reply_text(MEDITATIONS["breathing"])
        user_stats[user_id]["meditations"] += 1
    elif text == "🧘 Осознанность":
        await update.message.reply_text(MEDITATIONS["mindfulness"])
        user_stats[user_id]["meditations"] += 1
    elif text == "💪 Снятие стресса":
        await update.message.reply_text(MEDITATIONS["stress_relief"])
        user_stats[user_id]["meditations"] += 1
    elif text == "😴 Перед сном":
        await update.message.reply_text(MEDITATIONS["sleep"])
        user_stats[user_id]["meditations"] += 1
    
    # ===== УПРАЖНЕНИЯ =====
    elif text == "📝 Упражнения":
        await show_exercises(update, context)
    elif text == "🙏 Благодарность":
        await update.message.reply_text(EXERCISES["gratitude"])
        user_stats[user_id]["exercises"] += 1
    elif text == "🌍 Заземление":
        await update.message.reply_text(EXERCISES["grounding"])
        user_stats[user_id]["exercises"] += 1
    elif text == "🔄 Переоценка":
        await update.message.reply_text(EXERCISES["reframe"])
        user_stats[user_id]["exercises"] += 1
    elif text == "💪 Аффирмации":
        await update.message.reply_text(EXERCISES["affirmations"])
        user_stats[user_id]["exercises"] += 1
    elif text == "📝 Дневник мыслей":
        await update.message.reply_text(EXERCISES["thought_diary"])
        user_stats[user_id]["exercises"] += 1
    
    # ===== ДРУГИЕ КНОПКИ =====
    elif text == "🎵 Звуки природы":
        await show_nature_sounds(update, context)
    elif text == "💬 Поддержка":
        await handle_support(update, context)
    elif text == "📓 Дневник":
        await handle_diary(update, context)
    elif text == "🆘 Помощь":
        await handle_emergency(update, context)
    elif text == "📊 Статистика":
        await show_stats(update, context)
    elif text == "ℹ️ О боте":
        await handle_about(update, context)
    elif text == "🔙 Главное меню":
        await start(update, context)
    else:
        await update.message.reply_text(
            "Используйте кнопки меню для навигации.\n\n"
            "🧘 **Медитации** — 4 практики осознанности\n"
            "📝 **Упражнения** — 5 психологических техник\n"
            "🎵 **Звуки природы** — для релаксации\n"
            "💬 **Поддержка** — ободряющие сообщения\n"
            "📓 **Дневник** — сохранить мысли и чувства\n"
            "📊 **Статистика** — отслеживайте прогресс",
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
    
    logger.info("✅ Бот психологической поддержки запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
