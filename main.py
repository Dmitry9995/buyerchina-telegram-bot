#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from flask import Flask, request, jsonify
import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Токен бота
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not found!")
    exit(1)

BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
logger.info(f"Bot initialized: {BOT_TOKEN[:10]}...")

@app.route('/')
def health():
    return "🇨🇳 BuyerChina Bot is running on Railway!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logger.info(f"Received update: {data}")
        
        if 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            user_name = message.get('from', {}).get('first_name', 'Пользователь')
            
            if 'text' in message and message['text'] == '/start':
                welcome_text = (
                    f"🇨🇳 *Добро пожаловать в BuyerChina, {user_name}!*\n\n"
                    "Ваш помощник для покупок в Китае.\n"
                    "Отправьте фото товара или его описание для поиска аналогов."
                )
                send_message(chat_id, welcome_text)
            elif 'photo' in message:
                response_text = (
                    f"📸 *Получил фото от {user_name}!*\n\n"
                    "🔍 Анализирую изображение...\n"
                    "🇨🇳 Ищу аналогичные товары в Китае...\n"
                    "💰 Сравниваю цены у разных поставщиков...\n\n"
                    "*Примерные результаты:*\n"
                    "🏭 Поставщик 1: Guangzhou Factory - $12.50\n"
                    "🏭 Поставщик 2: Shenzhen Manufacturer - $11.80\n"
                    "🏭 Поставщик 3: Yiwu Supplier - $13.20\n\n"
                    "✅ Рекомендуем: Shenzhen Manufacturer (лучшая цена)"
                )
                send_message(chat_id, response_text)
            elif 'text' in message:
                text = message['text']
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
                send_message(chat_id, response_text)
        
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

def send_message(chat_id, text):
    try:
        url = f"{BOT_URL}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, json=data, timeout=10)
        logger.info(f"Message sent to {chat_id}: {response.status_code}")
        return response.json()
    except Exception as e:
        logger.error(f"Send message error: {e}")

def setup_webhook():
    """Настройка webhook для Railway"""
    try:
        # Получаем URL от Railway
        railway_url = os.getenv('RAILWAY_PUBLIC_DOMAIN')
        if railway_url:
            webhook_url = f"https://{railway_url}/webhook"
        else:
            # Fallback URL - нужно заменить на ваш реальный URL
            webhook_url = f"https://web-production-ea35.up.railway.app/webhook"
        
        # Удаляем старый webhook
        delete_url = f"{BOT_URL}/deleteWebhook"
        requests.post(delete_url, timeout=10)
        
        # Устанавливаем новый webhook
        set_url = f"{BOT_URL}/setWebhook"
        data = {'url': webhook_url}
        response = requests.post(set_url, json=data, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            logger.info(f"✅ Webhook set: {webhook_url}")
            return True
        else:
            logger.error(f"❌ Webhook failed: {result}")
            return False
            
    except Exception as e:
        logger.error(f"Webhook setup error: {e}")
        return False

@app.route('/set_webhook')
def manual_webhook():
    """Ручная настройка webhook"""
    if setup_webhook():
        return "✅ Webhook установлен успешно!"
    else:
        return "❌ Ошибка установки webhook"

@app.route('/webhook_info')
def webhook_info():
    """Информация о webhook"""
    try:
        url = f"{BOT_URL}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        result = response.json()
        return result
    except Exception as e:
        return {"error": str(e)}

if __name__ == '__main__':
    # Настраиваем webhook при запуске
    setup_webhook()
    
    # Запускаем Flask приложение
    port = int(os.getenv('PORT', 5000))
    logger.info(f"🚀 Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
