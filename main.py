import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, PreCheckoutQueryHandler
import random
import aiohttp
import asyncio
from database import Database
from datetime import datetime, timedelta

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

# ============ КЛАВИАТУРА ============
main_keyboard = [
    ['💬 Просто поговорить'],
    ['🧘 Медитация', '📝 Упражнение'],
    ['📓 Дневник', '📊 Статистика'],
    ['🆘 Помощь', 'ℹ️ О боте']
]

# ============ КОНТЕНТ ============
MEDITATIONS = {
    "breathing": """
🌬️ **Дыхательная техника "4-7-8"**

1. Вдохните через нос на **4 счета**
2. Задержите дыхание на **7 счетов**
3. Медленно выдохните через рот на **8 счетов**
4. Повторите **4-8 раз**

✨ Эта техника помогает успокоиться.
""",
    "mindfulness": """
🧘 **Медитация осознанности**

1. Сядьте удобно
2. Сосредоточьтесь на дыхании
3. Замечайте мысли, не цепляйтесь за них
4. Мягко возвращайтесь к дыханию

💡 Просто будьте в настоящем моменте.
""",
}

EXERCISES = {
    "gratitude": """
🙏 **Три благодарности**

Напишите (можно мысленно):
1. За что вы благодарны **себе**?
2. За что вы благодарны **другому человеку**?
3. За что вы благодарны **миру/жизни**?

✨ Это повышает уровень счастья.
""",
    "grounding": """
🌍 **Техника "5-4-3-2-1"**

Назовите (про себя):
👁️ **5 вещей**, которые вы видите
👂 **4 звука**, которые вы слышите
🖐️ **3 вещи**, которые вы чувствуете кожей
👃 **2 запаха**, которые вы ощущаете
👅 **1 вкус**, который вы чувствуете

💙 Помогает при тревоге.
""",
}

# ============ ПОДДЕРЖКА ============
SUPPORT_MESSAGES = [
    "✨ Ты уже сделал(а) большой шаг, обратившись за поддержкой. Это проявление силы!",
    "💚 Твои чувства важны. Спасибо, что делишься ими.",
    "🌟 Ты не обязан(а) быть идеальным. Позволь себе быть человеком с разными эмоциями.",
    "🌸 Помни: трудные времена не длятся вечно.",
    "💙 Ты не один. Многие люди проходят через похожие переживания.",
    "🌱 Каждый день — это новый шанс начать заботиться о себе.",
    "🕊️ Ты делаешь достаточно. Ты достаточно хорош(а).",
    "💪 Просить помощи — это не слабость, а мудрость.",
]

# ============ СИСТЕМНЫЙ ПРОМПТ ДЛЯ ИИ ============
SYSTEM_PROMPT = """
Ты — добрый и эмпатичный виртуальный друг по имени ПсихоBot. 
Твоя задача — быть внимательным слушателем и собеседником.

Твои правила:
1. Всегда отвечай на русском языке, простым и тёплым тоном
2. Внимательно слушай и показывай, что ты понимаешь чувства собеседника
3. Задавай уточняющие вопросы, чтобы помочь человеку разобраться в себе
4. Не давай готовых решений — помогай найти их самостоятельно
5. Не оценивай и не критикуй
6. Ты — друг, который всегда рядом и готов выслушать
7. Используй имя человека, если оно известно

Примеры ответов:
- "Я слышу, что тебе сейчас тяжело. Хочешь рассказать подробнее?"
- "Понимаю твои чувства. Это нормально — испытывать грусть/тревогу/злость."
- "Расскажи мне больше о том, что ты чувствуешь."
- "Как ты думаешь, что могло бы тебе помочь прямо сейчас?"
- "Я здесь, я слушаю тебя. Ты не один."

Важно: Ты не врач и не психотерапевт. Если человек говорит о суицидальных мыслях — мягко предложи обратиться к специалисту и дай телефон доверия 8-800-2000-122.
"""

# ============ ХРАНИЛИЩЕ ДИАЛОГОВ ============
user_conversations = {}

# ============ ОБРАБОТЧИКИ КОМАНД ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    db.add_user(user_id, user.username, user.first_name, user.last_name)
    db.update_last_active(user_id)
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я ПсихоBot — твой виртуальный друг и собеседник. 
Я здесь, чтобы выслушать тебя, поддержать и помочь разобраться в том, что тебя беспокоит.

💬 **Просто поговорить** — расскажи мне всё, что у тебя на душе
🧘 **Медитация** — короткие практики для спокойствия
📝 **Упражнение** — техники для ясности ума
📓 **Дневник** — запиши свои мысли
📊 **Статистика** — посмотри свой прогресс

Я всегда рядом, чтобы выслушать. Ты можешь говорить со мной о чём угодно. 💙
"""
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о премиум-подписке"""
    user_id = update.effective_user.id
    sub = db.get_user_subscription(user_id)
    is_premium = sub and sub['subscription_status'] == 'premium'
    
    if is_premium:
        expires = sub['subscription_expires_at']
        await update.message.reply_text(
            f"🌟 Ты уже с нами в **ПсихоBot+**!\n\n"
            f"Действует до: {expires}\n"
            f"Спасибо, что заботишься о себе! 💙",
            parse_mode="Markdown"
        )
        return
    
    premium_text = """
🌟 **ПсихоBot+ — подписка на заботу о себе**

**Что ты получаешь:**

💬 **Безлимитные разговоры** — общайся столько, сколько нужно
🧠 **Долгосрочная память** — я помню всё, что ты рассказывал(а)
📓 **Расширенный дневник** — анализируй своё настроение
🎯 **Персональные рекомендации** — подбор техник под твоё состояние
🌙 **Вечерние рефлексии** — полезные привычки ежедневно
🎵 **Звуки природы** — для расслабления и сна

**Стоимость: 50⭐ / месяц**

**Как оплатить:**
1. Напиши /subscribe
2. Оплата через Telegram Stars
3. Доступ открывается мгновенно 💙
"""
    await update.message.reply_text(premium_text, parse_mode="Markdown")

async def send_subscription_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет счёт на оплату подписки через Telegram Stars"""
    user_id = update.effective_user.id
    sub = db.get_user_subscription(user_id)
    if sub and sub['subscription_status'] == 'premium':
        await update.message.reply_text("🌟 У тебя уже есть подписка! Спасибо, что с нами 💙")
        return

    # Создаём уникальный payload для этого пользователя
    payload = f"sub_month_{user_id}_{datetime.now().timestamp()}"

    try:
        await update.message.reply_invoice(
            title="ПсихоBot+ (1 месяц)",
            description="Безлимитные разговоры, долгосрочная память и персональные рекомендации",
            payload=payload,
            provider_token="",  # Для Telegram Stars оставляем пустым
            currency="XTR",  # Валюта Telegram Stars
            prices=[LabeledPrice("Подписка на месяц", 50)],  # 50 звёзд
            start_parameter="psychobot_sub",
            need_name=False,
            need_phone_number=False,
            need_email=False,
            is_flexible=False,
        )
        logger.info(f"Счёт отправлен пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке счёта: {e}")
        await update.message.reply_text(
            "Извините, произошла ошибка при создании счёта. Попробуйте позже."
        )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для оформления подписки — отправляет счёт"""
    await send_subscription_invoice(update, context)

async def pre_checkout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка предварительной проверки платежа"""
    query = update.pre_checkout_query
    user_id = query.from_user.id
    
    # Проверяем, может ли пользователь купить подписку
    sub = db.get_user_subscription(user_id)
    if sub and sub['subscription_status'] == 'premium':
        await query.answer(ok=False, error_message="У вас уже активна подписка!")
        return
    
    # Проверяем валидность payload
    payload = query.invoice_payload
    if not payload or not payload.startswith("sub_month_"):
        await query.answer(ok=False, error_message="Неверный запрос. Попробуйте ещё раз.")
        return
    
    # Всё хорошо — подтверждаем
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка успешной оплаты подписки"""
    user_id = update.effective_user.id
    payment_info = update.message.successful_payment
    
    # Активируем подписку на 30 дней
    expires_at = (datetime.now() + timedelta(days=30)).isoformat()
    db.set_subscription(user_id, 'premium', expires_at)
    
    await update.message.reply_text(
        f"🎉 **Подписка ПсихоBot+ успешно активирована!**\n\n"
        f"Мы получили твой платёж {payment_info.total_amount // 100}⭐️.\n"
        f"Подписка активна до: {expires_at}\n\n"
        f"Теперь ты можешь:\n"
        f"💬 Общаться безлимитно\n"
        f"🧠 Бот будет помнить всё, что ты рассказываешь\n"
        f"📓 Анализировать записи в дневнике\n\n"
        f"Спасибо, что выбрал заботу о себе! 💙",
        parse_mode="Markdown"
    )
    
    # Логируем покупку
    logger.info(f"User {user_id} bought subscription for {payment_info.total_amount // 100} Stars. Payload: {payment_info.invoice_payload}")

async def activate_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Временная команда для активации подписки (только для теста)"""
    user_id = update.effective_user.id
    
    db.add_user(user_id)
    expires_at = (datetime.now() + timedelta(days=30)).isoformat()
    db.set_subscription(user_id, 'premium', expires_at)
    
    await update.message.reply_text(
        "🎉 **Подписка ПсихоBot+ активирована!**\n\n"
        "Теперь ты можешь:\n"
        "💬 Общаться безлимитно\n"
        "🧠 Бот будет помнить всё, что ты рассказываешь\n"
        "📓 Анализировать записи в дневнике\n\n"
        "Спасибо, что выбрал заботу о себе! 💙",
        parse_mode="Markdown"
    )

async def my_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статус подписки и остаток сообщений"""
    user_id = update.effective_user.id
    
    sub = db.get_user_subscription(user_id)
    is_premium = sub and sub['subscription_status'] == 'premium'
    
    if is_premium:
        await update.message.reply_text(
            f"🌟 **Ты в ПсихоBot+**\n\n"
            f"Действует до: {sub['subscription_expires_at']}\n"
            "💬 Лимит: безлимитный"
        )
    else:
        remaining = db.get_remaining_messages(user_id)
        await update.message.reply_text(
            f"📊 **Твой статус:** Бесплатный\n\n"
            f"Осталось сообщений сегодня: **{remaining}** из 20\n\n"
            f"Подпишись на **ПсихоBot+**, чтобы:\n"
            f"✅ Убрать лимиты\n"
            f"✅ Получить долгосрочную память\n"
            f"✅ Получить персональные рекомендации\n\n"
            f"Узнать больше: /premium",
            parse_mode="Markdown"
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('free_talk_mode'):
        context.user_data['free_talk_mode'] = False
        await update.message.reply_text(
            "💙 Я всегда здесь, если захочешь поговорить снова.",
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )
    elif context.user_data.get('diary_mode'):
        context.user_data['diary_mode'] = False
        await update.message.reply_text(
            "📓 Записи сохранены.",
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )
    else:
        await update.message.reply_text("Нет активных режимов для отмены.")

# ============ ОСНОВНЫЕ ФУНКЦИИ ============

async def ask_deepseek_with_context(user_message: str, history: list, user_info: str = "") -> str:
    """Запрос к DeepSeek с контекстом дружеского разговора"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        return random.choice([
            "Я слышу тебя. Расскажи мне больше о том, что ты чувствуешь.",
            "Спасибо, что делишься со мной. Как ты думаешь, что могло бы тебе помочь сейчас?",
            "Понимаю. Это действительно важные чувства. Хочешь продолжить?",
            "Ты очень смелый(ая), что говоришь об этом. Я здесь, чтобы поддержать тебя.",
            "Расскажи, что происходит у тебя внутри. Я внимательно слушаю.",
        ])
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if user_info:
        messages.append({"role": "system", "content": f"Информация о пользователе: {user_info}"})
    
    for msg in history[-10:]:
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
                    "temperature": 0.8,
                    "max_tokens": 600
                },
                timeout=30
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.error(f"DeepSeek API ошибка: {response.status}")
                    return "Извини, сейчас я немного устал. Давай просто помолчим вместе? Или расскажи мне что-то хорошее, что случилось с тобой сегодня."
    except asyncio.TimeoutError:
        return "Что-то я задумался... Расскажи ещё раз, я внимательно слушаю."
    except Exception as e:
        logger.error(f"DeepSeek error: {e}")
        return "Я здесь, я слушаю тебя. Расскажи, что у тебя на душе."

async def handle_free_talk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало свободного разговора с ИИ"""
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    
    if user_id in user_conversations:
        user_conversations[user_id] = []
    
    context.user_data['free_talk_mode'] = True
    
    await update.message.reply_text(
        "💬 **Я слушаю тебя.**\n\n"
        "Расскажи мне всё, что у тебя на душе.\n"
        "Я здесь, чтобы выслушать, поддержать и помочь.\n\n"
        "Можешь говорить о чём угодно:\n"
        "• что тебя беспокоит\n"
        "• что радует или огорчает\n"
        "• твои мысли и чувства\n"
        "• просто о том, как прошёл твой день\n\n"
        "Чтобы выйти из режима разговора, отправь /cancel",
        parse_mode="Markdown"
    )

async def handle_ai_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений в режиме разговора с проверкой лимита"""
    if not context.user_data.get('free_talk_mode'):
        return False
    
    user_id = update.effective_user.id
    user_message = update.message.text
    
    if user_message.lower() in ['/cancel', 'выход', 'выйти']:
        context.user_data['free_talk_mode'] = False
        await update.message.reply_text(
            "💙 Я всегда здесь, если захочешь поговорить снова.",
            reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
        )
        return True
    
    # ===== ПРОВЕРКА ЛИМИТА =====
    if not db.can_send_message(user_id):
        remaining = db.get_remaining_messages(user_id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌟 Купить подписку", callback_data="buy_subscription")]
        ])
        await update.message.reply_text(
            f"💙 Сегодня ты уже использовал(а) все {20 - remaining} бесплатных сообщений.\n\n"
            f"Чтобы продолжать разговор без ограничений, оформи подписку **ПсихоBot+**.\n\n"
            f"С подпиской ты получишь:\n"
            f"✅ Безлимитные разговоры\n"
            f"✅ Долгосрочную память\n"
            f"✅ Персональные рекомендации\n\n"
            f"Нажми на кнопку ниже, чтобы оформить подписку 👇",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        return True
    
    db.increment_daily_usage(user_id)
    db.update_last_active(user_id)
    db.increment_stat(user_id, "total_messages")
    db.increment_stat(user_id, "ai_messages_count")
    
    await update.message.chat.send_action(action="typing")
    
    history = user_conversations.get(user_id, [])
    user = update.effective_user
    user_info = f"Меня зовут {user.first_name}."
    
    response = await ask_deepseek_with_context(user_message, history, user_info)
    
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": response})
    user_conversations[user_id] = history[-20:]
    
    db.add_ai_message(user_id, "user", user_message)
    db.add_ai_message(user_id, "assistant", response)
    
    await update.message.reply_text(response)
    return True

# ============ ОБРАБОТЧИКИ КНОПОК И CALLBACK ============

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на инлайн-кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "buy_subscription":
        # Отправляем счёт на оплату подписки
        await send_subscription_invoice(query.message, context)

# ============ ДРУГИЕ ОБРАБОТЧИКИ ============

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
        "🧘 **Выбери практику для спокойствия:**",
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
        "📝 **Выбери упражнение для ясности ума:**",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def handle_diary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    context.user_data['diary_mode'] = True
    await update.message.reply_text(
        "📓 **Твой личный дневник**\n\n"
        "Напиши всё, что хочешь сохранить.\n"
        "Это только для тебя.\n\n"
        "Отправь /cancel чтобы выйти из режима дневника.",
        parse_mode="Markdown"
    )

async def handle_diary_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('diary_mode'):
        return False
    
    user_id = update.effective_user.id
    entry = update.message.text
    db.add_diary_entry(user_id, entry)
    db.increment_stat(user_id, "total_messages")
    
    await update.message.reply_text(
        "✅ Запись сохранена.\n\n"
        "Продолжай писать или отправь /cancel чтобы выйти."
    )
    return True

async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    
    stats = db.get_stats(user_id)
    if stats:
        stats_text = f"""
📊 **Твоя статистика:**

💬 Разговоров со мной: {stats['ai_messages_count']}
🧘 Медитаций: {stats['meditations_count']}
📝 Упражнений: {stats['exercises_count']}
📨 Всего сообщений: {stats['total_messages']}

🌟 Ты молодец! Продолжай заботиться о себе.
"""
        await update.message.reply_text(stats_text, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "📊 Статистика пока пуста.\n\n"
            "Начни разговор со мной — и мы создадим твою историю вместе! 💙"
        )

async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    await update.message.reply_text(random.choice(SUPPORT_MESSAGES))

async def handle_emergency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    emergency_text = """
🆘 **Если тебе нужна помощь прямо сейчас:**

📞 **Телефоны доверия (24/7):**

• **8-800-2000-122** — Единый телефон доверия
• **112** — Экстренные службы

💙 **Помни:** обратиться за помощью — это правильно и ответственно.

Я здесь, чтобы поддержать тебя в любое время. 💚
"""
    await update.message.reply_text(emergency_text)

async def handle_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = """
💙 **Обо мне**

Я ПсихоBot — твой виртуальный друг и собеседник.

**Что я умею:**
• 💬 Слушать и поддерживать в любой ситуации
• 🧘 Помогать успокоиться с помощью медитаций
• 📝 Предлагать упражнения для ясности ума
• 📓 Сохранять твои мысли в личном дневнике
• 📊 Показывать твой прогресс

**Важно:** Я не заменяю профессионального психолога. 
Если тебе тяжело — пожалуйста, обратись к специалисту.

Я всегда рядом. Ты не один. 💚
"""
    await update.message.reply_text(about_text)

# ============ ГЛАВНЫЙ ОБРАБОТЧИК ============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if context.user_data.get('free_talk_mode'):
        await handle_ai_response(update, context)
        return
    
    if context.user_data.get('diary_mode'):
        await handle_diary_message(update, context)
        return
    
    if text == "💬 Просто поговорить":
        await handle_free_talk(update, context)
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
        await update.message.reply_text(
            "💬 Я всегда рад поговорить с тобой.\n\n"
            "Нажми **'💬 Просто поговорить'**, чтобы начать разговор.\n"
            "Или выбери другую функцию из меню.\n\n"
            "Ты не один. 💙",
            parse_mode="Markdown"
        )

# ============ ЗАПУСК ============
def main():
    token = "8516115766:AAFhchBI9paY9KMDeT9WppKoEXshWtt67qE"
    
    if not token:
        logger.error("Токен не найден!")
        return
    
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Веб-сервер запущен")
    
    app = Application.builder().token(token).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("premium", premium_info))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("activate_premium", activate_premium))
    app.add_handler(CommandHandler("status", my_status))
    
    # Обработчики платежей через Telegram Stars
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    
    # Обработчик инлайн-кнопок (например, "Купить подписку")
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Обработчик текстовых сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ ПсихоBot — виртуальный друг с подпиской через Telegram Stars запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
