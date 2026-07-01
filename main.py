import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, PreCheckoutQueryHandler, CallbackQueryHandler
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

1. Вдох через нос на **4 счета**
2. Задержка на **7 счетов**
3. Выдох через рот на **8 счетов**
4. Повторите **4-8 раз**

✨ Успокаивает нервную систему.
""",
    "mindfulness": """
🧘 **Медитация осознанности**

1. Сядьте удобно
2. Сосредоточьтесь на дыхании
3. Замечайте мысли, не цепляясь за них
4. Мягко возвращайтесь к дыханию

💡 Просто будьте в настоящем моменте.
""",
    "ocean_breath": """
🌊 **Дыхание океана**

Представьте, что ваше дыхание — это волны океана.

📋 **Инструкция:**
1. Сядьте удобно, закройте глаза
2. На вдохе представьте, как волна накатывает на берег
3. На выдохе — как волна отступает
4. Дышите плавно, без усилий
5. Продолжайте 5-7 минут

✨ Помогает успокоиться и отпустить напряжение.
""",
    "inner_light": """
🔥 **Внутренний свет**

Эта медитация наполняет вас теплом и энергией.

📋 **Инструкция:**
1. Закройте глаза и сделайте 3 глубоких вдоха
2. Представьте в груди мягкий тёплый свет
3. С каждым вдохом свет становится ярче и теплее
4. С каждым выдохом свет распространяется по всему телу
5. Позвольте этому теплу наполнить вас

✨ Даёт чувство внутренней опоры и спокойствия.
""",
    "forest_walk": """
🌿 **Прогулка по лесу**

Визуализация для расслабления и восстановления.

📋 **Инструкция:**
1. Закройте глаза, представьте красивый лес
2. Идите по тропинке, чувствуйте землю под ногами
3. Слышьте пение птиц и шелест листьев
4. Чувствуйте свежий воздух и запах сосен
5. Остановитесь на поляне, вдохните полной грудью
6. Побудьте в этом месте столько, сколько нужно

✨ Восстанавливает ресурсное состояние.
""",
    "self_forgiveness": """
✨ **Медитация прощения себя**

Эта практика помогает принять и отпустить прошлое.

📋 **Инструкция:**
1. Сядьте удобно, положите руку на сердце
2. Вспомните ситуацию, где вы себя осуждаете
3. Скажите мысленно: "Я прощаю себя за это"
4. Почувствуйте, как тяжесть уходит с каждым выдохом
5. Повторите несколько раз: "Я достоин(на) прощения"
6. Закончите с благодарностью к себе

💙 Помогает освободиться от чувства вины.
""",
    "moment_value": """
💎 **Ценность момента**

Осознанность здесь и сейчас.

📋 **Инструкция:**
1. Откройте глаза, осмотритесь вокруг
2. Найдите 5 вещей, которые вы раньше не замечали
3. Сосредоточьтесь на одном предмете, изучите его детали
4. Почувствуйте, что этот момент существует только сейчас
5. Позвольте себе быть полностью в этом мгновении

💡 Напоминает о ценности каждого мгновения.
""",
    "rainbow_emotions": """
🌈 **Радуга эмоций**

Работа с эмоциями через визуализацию цвета.

📋 **Инструкция:**
1. Закройте глаза и представьте радугу
2. Отметьте, какая эмоция сейчас у вас внутри
3. Подберите цвет, который её отражает
4. Мысленно вдохните этот цвет, наполнитесь им
5. На выдохе отпустите напряжение
6. Теперь представьте, что эмоция меняет цвет на более спокойный

🎨 Помогает осознать и принять свои чувства.
""",
    "morning_sun": """
☀️ **Утреннее солнце**

Энергичная медитация для начала дня.

📋 **Инструкция:**
1. Встаньте или сядьте с прямой спиной
2. Представьте, что вы встречаете восход солнца
3. С каждым вдохом вы вдыхаете солнечный свет
4. На выдохе посылаете лучи солнца всему телу
5. Чувствуйте, как энергия наполняет каждую клетку
6. Откройте глаза с лёгкой улыбкой

☀️ Даёт заряд бодрости на весь день.
""",
    "night_moon": """
🌙 **Лунная ночь**

Глубокая релаксация перед сном.

📋 **Инструкция:**
1. Лягте в постель, закройте глаза
2. Представьте ночное небо с луной
3. С каждым выдохом вы становитесь легче
4. Лунный свет мягко окутывает всё тело
5. Позвольте себе полностью расслабиться
6. Слейтесь с тишиной и покоем ночи

💤 Помогает заснуть и восстановиться.
""",
    "open_heart": """
🌺 **Открытое сердце**

Практика на любовь и доброту к себе.

📋 **Инструкция:**
1. Сядьте, положите руки на сердце
2. Вспомните момент, когда вы были добры к себе
3. Почувствуйте тепло в груди
4. На вдохе наполняйте это тепло
5. На выдохе отправляйте любовь себе
6. Повторите: "Я люблю себя, я принимаю себя"

💚 Создаёт чувство безусловного принятия.
""",
    "centering": """
🎯 **Центрирование**

Быстрая техника для фокуса и спокойствия.

📋 **Инструкция:**
1. Встаньте, почувствуйте твёрдую опору под ногами
2. Представьте, что из центра тела растёт стержень
3. Вытянитесь мысленно вверх и вниз одновременно
4. Ощутите баланс и устойчивость
5. Побудьте в этом центрированном состоянии 2-3 минуты

🎯 Помогает быстро собраться в стрессовой ситуации.
""",
}

EXERCISES = {
    "gratitude": """
🙏 **Три благодарности**

Напишите (можно мысленно):
1. За что вы благодарны **себе**?
2. За что вы благодарны **другому человеку**?
3. За что вы благодарны **миру/жизни**?

✨ Исследования показывают: ежедневная практика благодарности повышает уровень счастья на 25%.
""",
    "grounding": """
🌍 **Техника "5-4-3-2-1"**

Назовите (про себя):
👁️ **5 вещей**, которые вы видите
👂 **4 звука**, которые вы слышите
🖐️ **3 вещи**, которые вы чувствуете кожей
👃 **2 запаха**, которые вы ощущаете
👅 **1 вкус**, который вы чувствуете

💙 Помогает при тревоге и панических атаках.
""",
    "success_diary": """
📋 **Дневник успеха**

Запишите прямо сейчас:
1. Одно достижение за сегодня (даже маленькое)
2. Одно дело, которое вы сделали хорошо
3. Один шаг, который вы сделали вперёд

💫 Это упражнение повышает самооценку и уверенность.
""",
    "observer": """
🔍 **Упражнение "Наблюдатель"**

Практика отделения от мыслей.

📋 **Инструкция:**
1. Сядьте и закройте глаза
2. Представьте, что вы сидите на берегу реки
3. Ваши мысли — это листья, плывущие по реке
4. Просто наблюдайте, как они проплывают мимо
5. Не цепляйтесь за них, не оценивайте
6. Позвольте им течь свободно

💡 Помогает не отождествляться с негативными мыслями.
""",
    "self_hug": """
🤗 **Объятие себя**

Физическая практика самоподдержки.

📋 **Инструкция:**
1. Сядьте или встаньте удобно
2. Обнимите себя за плечи
3. Почувствуйте тепло своих рук
4. Скажите мысленно: "Я с тобой, я рядом"
5. Побудьте в этом объятии 1-2 минуты
6. Почувствуйте, как тело расслабляется

💙 Дарит ощущение безопасности и поддержки.
""",
    "focus_shift": """
💭 **Смена фокуса**

Перенос внимания с проблемы на ресурсы.

📋 **Инструкция:**
1. Напишите одну проблему, которая вас беспокоит
2. Напишите 3 ресурса, которые у вас есть:
   • Ваши сильные качества
   • Люди, которые могут поддержать
   • Что уже помогает вам справляться
3. Перечитайте список ресурсов
4. Почувствуйте, как меняется ваше состояние

🔄 Помогает увидеть ситуацию с другой стороны.
""",
    "joy_planning": """
📅 **Планирование радости**

Запланируйте 3 приятных события на неделю:
1. ___________
2. ___________
3. ___________

Это могут быть маленькие радости:
• прогулка в парке
• любимый фильм
• звонок другу
• чашка хорошего чая

✨ Создаёт привычку заботиться о себе.
""",
    "power_words": """
💪 **Сила слова**

Работа с ключевыми убеждениями.

📋 **Инструкция:**
1. Запишите 2-3 убеждения, которые вас ограничивают
2. Перепишите их в поддерживающие
3. Повторите новые фразы 3 раза вслух
4. Почувствуйте, как они звучат внутри вас

💡 Меняет внутренний диалог на поддерживающий.
""",
    "my_roots": """
🌳 **Мои корни**

Рефлексия на опору и поддержку.

📋 **Инструкция:**
1. Вспомните людей, которые вас поддерживают
2. Что даёт вам силы в трудные моменты?
3. Какие ваши ценности являются опорой?
4. Запишите 3 источника вашей силы
5. Почувствуйте, как эти корни держат вас

🌱 Укрепляет чувство устойчивости и защищённости.
""",
    "creative_flow": """
🎨 **Творческий поток**

5 минут свободного выражения.

📋 **Инструкция:**
1. Возьмите лист бумаги и ручку
2. Рисуйте или пишите всё, что приходит в голову
3. Не оценивайте, не исправляйте
4. Позвольте руке двигаться свободно
5. Просто будьте в потоке творчества

🎨 Помогает выразить эмоции через творчество.
""",
    "my_boundaries": """
🛡️ **Мои границы**

Практика на осознание личных границ.

📋 **Инструкция:**
1. Вспомните ситуацию, где вы чувствовали дискомфорт
2. Напишите: "Моей границей было..."
3. Что вы чувствовали в тот момент?
4. Что бы вы хотели сказать или сделать иначе?
5. Сформулируйте новое правило для себя

💙 Помогает осознать и защитить свои границы.
""",
    "my_value": """
🏆 **Моя ценность**

Упражнение на самоценность.

📋 **Инструкция:**
1. Напишите 5 качеств, за которые вы себя цените
2. Напишите 3 ситуации, где вы проявили эти качества
3. Вспомните, как вы помогли кому-то или себе
4. Прочитайте всё написанное вслух
5. Скажите себе: "Я важен(на), я ценен(на)"

🌟 Укрепляет чувство собственной значимости.
""",
}

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

user_conversations = {}

# ============ ОБРАБОТЧИКИ КОМАНД ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    db.add_user(user_id, user.username, user.first_name, user.last_name)
    db.update_last_active(user_id)
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}! Я ПсихоBot — твой виртуальный друг и собеседник. Я здесь, чтобы выслушать тебя, поддержать и помочь разобраться в том, что тебя беспокоит.",
        reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True),
        parse_mode="Markdown"
    )

async def premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = db.get_user_subscription(user_id)
    is_premium = sub and sub['subscription_status'] == 'premium'
    if is_premium:
        await update.message.reply_text(f"🌟 Ты уже с нами в **ПсихоBot+**!\n\nДействует до: {sub['subscription_expires_at']}\nСпасибо, что заботишься о себе! 💙", parse_mode="Markdown")
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
"""
    await update.message.reply_text(premium_text, parse_mode="Markdown")

async def send_subscription_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = db.get_user_subscription(user_id)
    if sub and sub['subscription_status'] == 'premium':
        await update.message.reply_text("🌟 У тебя уже есть подписка! Спасибо, что с нами 💙")
        return
    payload = f"sub_month_{user_id}_{datetime.now().timestamp()}"
    try:
        await update.message.reply_invoice(
            title="ПсихоBot+ (1 месяц)",
            description="Безлимитные разговоры, долгосрочная память и персональные рекомендации",
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice("Подписка на месяц", 50)],
            start_parameter="psychobot_sub",
            need_name=False,
            need_phone_number=False,
            need_email=False,
            is_flexible=False,
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке счёта: {e}")
        await update.message.reply_text("Извините, произошла ошибка при создании счёта. Попробуйте позже.")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_subscription_invoice(update, context)

async def pre_checkout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    user_id = query.from_user.id
    sub = db.get_user_subscription(user_id)
    if sub and sub['subscription_status'] == 'premium':
        await query.answer(ok=False, error_message="У вас уже активна подписка!")
        return
    payload = query.invoice_payload
    if not payload or not payload.startswith("sub_month_"):
        await query.answer(ok=False, error_message="Неверный запрос. Попробуйте ещё раз.")
        return
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payment_info = update.message.successful_payment
    expires_at = (datetime.now() + timedelta(days=30)).isoformat()
    db.set_subscription(user_id, 'premium', expires_at)
    await update.message.reply_text(
        f"🎉 **Подписка ПсихоBot+ успешно активирована!**\n\nМы получили твой платёж {payment_info.total_amount // 100}⭐️.\nПодписка активна до: {expires_at}\n\nСпасибо, что выбрал заботу о себе! 💙",
        parse_mode="Markdown"
    )
    logger.info(f"User {user_id} bought subscription for {payment_info.total_amount // 100} Stars.")

async def activate_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.add_user(user_id)
    expires_at = (datetime.now() + timedelta(days=30)).isoformat()
    db.set_subscription(user_id, 'premium', expires_at)
    await update.message.reply_text(
        "🎉 **Подписка ПсихоBot+ активирована!**\n\nТеперь ты можешь:\n💬 Общаться безлимитно\n🧠 Бот будет помнить всё, что ты рассказываешь\n📓 Анализировать записи в дневнике\n\nСпасибо, что выбрал заботу о себе! 💙",
        parse_mode="Markdown"
    )

async def my_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = db.get_user_subscription(user_id)
    is_premium = sub and sub['subscription_status'] == 'premium'
    if is_premium:
        await update.message.reply_text(f"🌟 **Ты в ПсихоBot+**\n\nДействует до: {sub['subscription_expires_at']}\n💬 Лимит: безлимитный")
    else:
        remaining = db.get_remaining_messages(user_id)
        await update.message.reply_text(
            f"📊 **Твой статус:** Бесплатный\n\nОсталось сообщений сегодня: **{remaining}** из 20\n\nПодпишись на **ПсихоBot+**, чтобы:\n✅ Убрать лимиты\n✅ Получить долгосрочную память\n✅ Получить персональные рекомендации\n\nУзнать больше: /premium",
            parse_mode="Markdown"
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('free_talk_mode'):
        context.user_data['free_talk_mode'] = False
        await update.message.reply_text("💙 Я всегда здесь, если захочешь поговорить снова.", reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True))
    elif context.user_data.get('diary_mode'):
        context.user_data['diary_mode'] = False
        await update.message.reply_text("📓 Записи сохранены.", reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True))
    else:
        await update.message.reply_text("Нет активных режимов для отмены.")

# ============ ОСНОВНЫЕ ФУНКЦИИ ============

async def ask_deepseek_with_context(user_message: str, history: list, user_info: str = "") -> str:
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
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "messages": messages, "temperature": 0.8, "max_tokens": 600},
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
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    if user_id in user_conversations:
        user_conversations[user_id] = []
    context.user_data['free_talk_mode'] = True
    await update.message.reply_text(
        "💬 **Я слушаю тебя.**\n\nРасскажи мне всё, что у тебя на душе.\nЯ здесь, чтобы выслушать, поддержать и помочь.\n\nМожешь говорить о чём угодно:\n• что тебя беспокоит\n• что радует или огорчает\n• твои мысли и чувства\n• просто о том, как прошёл твой день\n\nЧтобы выйти из режима разговора, отправь /cancel",
        parse_mode="Markdown"
    )

async def handle_ai_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('free_talk_mode'):
        return False
    user_id = update.effective_user.id
    user_message = update.message.text
    if user_message.lower() in ['/cancel', 'выход', 'выйти']:
        context.user_data['free_talk_mode'] = False
        await update.message.reply_text("💙 Я всегда здесь, если захочешь поговорить снова.", reply_markup=ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True))
        return True
    if not db.can_send_message(user_id):
        remaining = db.get_remaining_messages(user_id)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🌟 Купить подписку", callback_data="buy_subscription")]])
        await update.message.reply_text(
            f"💙 Сегодня ты уже использовал(а) все {20 - remaining} бесплатных сообщений.\n\nЧтобы продолжать разговор без ограничений, оформи подписку **ПсихоBot+**.\n\nС подпиской ты получишь:\n✅ Безлимитные разговоры\n✅ Долгосрочную память\n✅ Персональные рекомендации\n\nНажми на кнопку ниже, чтобы оформить подписку 👇",
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

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "buy_subscription":
        await send_subscription_invoice(query.message, context)

async def handle_meditation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    db.increment_stat(user_id, "meditations_count")
    keyboard = [
        ['🌬️ Дыхание 4-7-8', '🧘 Осознанность'],
        ['🌊 Дыхание океана', '🔥 Внутренний свет'],
        ['🌿 Лесная прогулка', '✨ Прощение себя'],
        ['💎 Ценность момента', '🌈 Радуга эмоций'],
        ['☀️ Утреннее солнце', '🌙 Лунная ночь'],
        ['🌺 Открытое сердце', '🎯 Центрирование'],
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
        ['🙏 Три благодарности', '🌍 Заземление'],
        ['📋 Дневник успеха', '🔍 Наблюдатель'],
        ['🤗 Объятие себя', '💭 Смена фокуса'],
        ['📅 Планирование радости', '💪 Сила слова'],
        ['🌳 Мои корни', '🎨 Творческий поток'],
        ['🛡️ Мои границы', '🏆 Моя ценность'],
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
        "📓 **Твой личный дневник**\n\nНапиши всё, что хочешь сохранить.\nЭто только для тебя.\n\nОтправь /cancel чтобы выйти из режима дневника.",
        parse_mode="Markdown"
    )

async def handle_diary_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('diary_mode'):
        return False
    user_id = update.effective_user.id
    entry = update.message.text
    db.add_diary_entry(user_id, entry)
    db.increment_stat(user_id, "total_messages")
    await update.message.reply_text("✅ Запись сохранена.\n\nПродолжай писать или отправь /cancel чтобы выйти.")
    return True

async def handle_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    stats = db.get_stats(user_id)
    if stats:
        await update.message.reply_text(
            f"📊 **Твоя статистика:**\n\n💬 Разговоров со мной: {stats['ai_messages_count']}\n🧘 Медитаций: {stats['meditations_count']}\n📝 Упражнений: {stats['exercises_count']}\n📨 Всего сообщений: {stats['total_messages']}\n\n🌟 Ты молодец! Продолжай заботиться о себе.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("📊 Статистика пока пуста.\n\nНачни разговор со мной — и мы создадим твою историю вместе! 💙")

async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_active(user_id)
    await update.message.reply_text(random.choice(SUPPORT_MESSAGES))

async def handle_emergency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 **Если тебе нужна помощь прямо сейчас:**\n\n📞 **Телефоны доверия (24/7):**\n• **8-800-2000-122** — Единый телефон доверия\n• **112** — Экстренные службы\n\n💙 **Помни:** обратиться за помощью — это правильно и ответственно.\n\nЯ здесь, чтобы поддержать тебя в любое время. 💚"
    )

async def handle_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💙 **Обо мне**\n\nЯ ПсихоBot — твой виртуальный друг и собеседник.\n\n**Что я умею:**\n• 💬 Слушать и поддерживать в любой ситуации\n• 🧘 Помогать успокоиться с помощью медитаций\n• 📝 Предлагать упражнения для ясности ума\n• 📓 Сохранять твои мысли в личном дневнике\n• 📊 Показывать твой прогресс\n\n**Важно:** Я не заменяю профессионального психолога. Если тебе тяжело — пожалуйста, обратись к специалисту.\n\nЯ всегда рядом. Ты не один. 💚"
    )

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
    elif text == "🌊 Дыхание океана":
        await update.message.reply_text(MEDITATIONS["ocean_breath"])
    elif text == "🔥 Внутренний свет":
        await update.message.reply_text(MEDITATIONS["inner_light"])
    elif text == "🌿 Лесная прогулка":
        await update.message.reply_text(MEDITATIONS["forest_walk"])
    elif text == "✨ Прощение себя":
        await update.message.reply_text(MEDITATIONS["self_forgiveness"])
    elif text == "💎 Ценность момента":
        await update.message.reply_text(MEDITATIONS["moment_value"])
    elif text == "🌈 Радуга эмоций":
        await update.message.reply_text(MEDITATIONS["rainbow_emotions"])
    elif text == "☀️ Утреннее солнце":
        await update.message.reply_text(MEDITATIONS["morning_sun"])
    elif text == "🌙 Лунная ночь":
        await update.message.reply_text(MEDITATIONS["night_moon"])
    elif text == "🌺 Открытое сердце":
        await update.message.reply_text(MEDITATIONS["open_heart"])
    elif text == "🎯 Центрирование":
        await update.message.reply_text(MEDITATIONS["centering"])
    elif text == "🙏 Три благодарности":
        await update.message.reply_text(EXERCISES["gratitude"])
    elif text == "🌍 Заземление":
        await update.message.reply_text(EXERCISES["grounding"])
    elif text == "📋 Дневник успеха":
        await update.message.reply_text(EXERCISES["success_diary"])
    elif text == "🔍 Наблюдатель":
        await update.message.reply_text(EXERCISES["observer"])
    elif text == "🤗 Объятие себя":
        await update.message.reply_text(EXERCISES["self_hug"])
    elif text == "💭 Смена фокуса":
        await update.message.reply_text(EXERCISES["focus_shift"])
    elif text == "📅 Планирование радости":
        await update.message.reply_text(EXERCISES["joy_planning"])
    elif text == "💪 Сила слова":
        await update.message.reply_text(EXERCISES["power_words"])
    elif text == "🌳 Мои корни":
        await update.message.reply_text(EXERCISES["my_roots"])
    elif text == "🎨 Творческий поток":
        await update.message.reply_text(EXERCISES["creative_flow"])
    elif text == "🛡️ Мои границы":
        await update.message.reply_text(EXERCISES["my_boundaries"])
    elif text == "🏆 Моя ценность":
        await update.message.reply_text(EXERCISES["my_value"])
    else:
        await update.message.reply_text(
            "💬 Я всегда рад поговорить с тобой.\n\nНажми **'💬 Просто поговорить'**, чтобы начать разговор.\nИли выбери другую функцию из меню.\n\nТы не один. 💙",
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
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("premium", premium_info))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("activate_premium", activate_premium))
    app.add_handler(CommandHandler("status", my_status))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("✅ ПсихоBot — виртуальный друг с подпиской через Telegram Stars и расширенным контентом запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
