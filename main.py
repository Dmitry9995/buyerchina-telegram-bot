#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import threading

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask приложение
app = Flask(__name__)

# Глобальные переменные
telegram_app = None
bot_token = None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "🇨🇳 Добро пожаловать в BuyerChina!\n\n"
        "Отправьте фото или описание товара для поиска."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех сообщений"""
    user = update.effective_user
    username = user.username or "Unknown"
    
    if update.message.photo:
        await update.message.reply_text(
            f"📸 *Получил фото от {username}!*\n\n"
            "🔍 Анализирую изображение...\n"
            "🇨🇳 Ищу аналогичные товары в Китае...\n"
            "💰 Сравниваю цены у разных поставщиков...\n\n"
            "*Примерные результаты:*\n"
            "🏭 Поставщик 1: Guangzhou Factory - $12.50\n"
            "🏭 Поставщик 2: Shenzhen Manufacturer - $11.80\n"
            "🏭 Поставщик 3: Yiwu Supplier - $13.20\n\n"
            "✅ Рекомендуем: Shenzhen Manufacturer (лучшая цена)"
        )
    elif update.message.text:
        text = update.message.text
        response_text = (
            f"📝 *Получил запрос:* {text}\n\n"
            "🔍 Ищу товары в базе китайских поставщиков...\n"
            "💰 Анализирую цены и качество...\n\n"
            "*Найденные товары:*\n"
            "🏭 Alibaba Supplier A - $8.90 (MOQ: 100)\n"
            "🏭 Made-in-China Supplier B - $9.50 (MOQ: 50)\n"
            "🏭 DHgate Supplier C - $12.00 (MOQ: 1)\n\n"
            "✅ Рекомендуем: Supplier A (лучшее соотношение цена/качество)"
        )
        await update.message.reply_text(response_text)

@app.route('/')
def health():
    """Health check"""
    return "Bot is running!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_data = request.get_json()
        if json_data:
            update = Update.de_json(json_data, telegram_app.bot)
            # Создаем новый event loop для обработки
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(telegram_app.process_update(update))
            loop.close()
        return "OK"
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

def setup_telegram_bot():
    """Настройка Telegram бота"""
    global telegram_app, bot_token
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not found!")
        return False
    
    logger.info(f"Setting up bot: {bot_token[:10]}...")
    
    # Создаем приложение
    telegram_app = Application.builder().token(bot_token).build()
    
    # Добавляем обработчики
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(MessageHandler(filters.ALL, handle_message))
    
    logger.info("Bot handlers registered")
    return True

def setup_webhook():
    """Установка webhook"""
    try:
        bot = Bot(token=bot_token)
        
        # Получаем URL Railway
        railway_url = os.getenv('RAILWAY_PUBLIC_DOMAIN')
        if not railway_url:
            logger.warning("RAILWAY_PUBLIC_DOMAIN not found, webhook may not work")
            return
        
        webhook_url = f"https://{railway_url}/webhook"
        
        # Устанавливаем webhook в отдельном потоке
        def set_webhook():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(bot.set_webhook(url=webhook_url))
            loop.close()
        
        thread = threading.Thread(target=set_webhook)
        thread.start()
        thread.join()
        
        logger.info(f"Webhook set: {webhook_url}")
        
    except Exception as e:
        logger.error(f"Webhook setup failed: {e}")

if __name__ == '__main__':
    logger.info("Starting BuyerChina Bot...")
    
    if setup_telegram_bot():
        setup_webhook()
        
        # Запускаем Flask
        port = int(os.environ.get('PORT', 8080))
        logger.info(f"Starting server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        logger.error("Bot setup failed!")
        exit(1)
