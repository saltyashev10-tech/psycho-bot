import os
import logging
from telegram.ext import Application, CommandHandler

logging.basicConfig(level=logging.INFO)

async def start(update, context):
    await update.message.reply_text("✅ Бот работает на Render 24/7!")

def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not TOKEN:
        print("❌ Токен не найден!")
        return
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    print("🚀 Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
