#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from datetime import datetime
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

# Настройки менеджера
MANAGER_CHAT_ID = os.getenv('MANAGER_CHAT_ID', '1169659218')  # ID чата менеджера

def create_order_id(user_id):
    """Создание ID заказа без Google Sheets"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        order_id = f"ORD-{user_id}-{timestamp}"
        logger.info(f"✅ Created order ID: {order_id}")
        return order_id
    except Exception as e:
        logger.error(f"Error creating order ID: {e}")
        return "ORD-ERROR"

def send_message(chat_id, text):
    """Отправка сообщения в Telegram"""
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
        return None

def notify_manager(user_id, username, user_name, message_type, content, order_id=None):
    """Уведомление менеджера о новом запросе"""
    try:
        if message_type == "photo":
            notification_text = (
                f"📸 *НОВЫЙ ЗАПРОС - ФОТО*\n\n"
                f"👤 Пользователь: {user_name} (@{username if username else 'без username'})\n"
                f"🆔 ID: `{user_id}`\n"
                f"📋 Заказ: `{order_id if order_id else 'N/A'}`\n\n"
                f"📝 Пользователь загрузил фото товара для поиска аналогов в Китае.\n\n"
                f"⏰ *Требуется связаться в течение 15 минут!*"
            )
        else:
            notification_text = (
                f"📝 *НОВЫЙ ЗАПРОС - ТЕКСТ*\n\n"
                f"👤 Пользователь: {user_name} (@{username if username else 'без username'})\n"
                f"🆔 ID: `{user_id}`\n"
                f"📋 Заказ: `{order_id if order_id else 'N/A'}`\n\n"
                f"💬 Запрос: _{content[:200] if content else 'N/A'}..._\n\n"
                f"⏰ *Требуется связаться в течение 15 минут!*"
            )
        
        # Отправляем уведомление менеджеру
        send_message(MANAGER_CHAT_ID, notification_text)
        logger.info(f"✅ Manager notified about request from user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to notify manager: {e}")
        return False

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
            user_data = message.get('from', {})
            user_id = user_data.get('id')
            user_name = user_data.get('first_name', 'Пользователь')
            username = user_data.get('username', '')
            last_name = user_data.get('last_name', '')
            language = user_data.get('language_code', '')
            
            if 'text' in message and message['text'] == '/start':
                welcome_text = (
                    f"🇨🇳 *Добро пожаловать в BuyerChina, {user_name}!*\n\n"
                    "Ваш помощник для покупок в Китае.\n"
                    "Отправьте фото товара или его описание для поиска аналогов."
                )
                send_message(chat_id, welcome_text)
                
            elif 'photo' in message:
                # Создаем ID заказа
                order_id = create_order_id(user_id)
                
                # Уведомляем менеджера
                notify_manager(user_id, username, user_name, "photo", "Photo uploaded", order_id)
                
                response_text = (
                    f"📸 *Спасибо за фото, {user_name}!*\n\n"
                    "✅ *Ваша заявка принята в обработку*\n\n"
                    "👨‍💼 Наш менеджер уже получил уведомление и свяжется с вами в ближайшие *15 минут* или в удобное для вас время.\n\n"
                    "🔍 Мы найдем лучшие предложения от проверенных поставщиков в Китае:\n"
                    "• Анализ качества и цен\n"
                    "• Проверка надежности поставщика\n"
                    "• Помощь с доставкой и таможней\n\n"
                    f"📋 Номер заявки: `{order_id}`\n\n"
                    "💬 Если у вас срочный вопрос, напишите напрямую!"
                )
                send_message(chat_id, response_text)
                
            elif 'text' in message:
                text = message['text']
                
                # Создаем ID заказа
                order_id = create_order_id(user_id)
                
                # Уведомляем менеджера
                notify_manager(user_id, username, user_name, "text", text, order_id)
                
                response_text = (
                    f"📝 *Спасибо за запрос, {user_name}!*\n\n"
                    f"💬 Ваш запрос: _{text}_\n\n"
                    "✅ *Заявка принята в обработку*\n\n"
                    "👨‍💼 Наш менеджер уже получил уведомление и свяжется с вами в ближайшие *15 минут* или в удобное для вас время.\n\n"
                    "🇨🇳 Мы найдем для вас:\n"
                    "• Лучшие цены от проверенных поставщиков\n"
                    "• Качественные аналоги товара\n"
                    "• Помощь с оформлением и доставкой\n"
                    "• Консультацию по таможенному оформлению\n\n"
                    f"📋 Номер заявки: `{order_id}`\n\n"
                    "💬 Для срочных вопросов пишите напрямую!"
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

def notify_manager(user_id, username, user_name, message_type, content, order_id=None):
    """Уведомление менеджера о новом запросе"""
    try:
        if message_type == "photo":
            notification_text = (
                f"📸 *НОВЫЙ ЗАПРОС - ФОТО*\n\n"
                f"👤 Пользователь: {user_name} (@{username if username else 'без username'})\n"
                f"🆔 ID: `{user_id}`\n"
                f"📋 Заказ: `{order_id if order_id else 'N/A'}`\n\n"
                f"📝 Пользователь загрузил фото товара для поиска аналогов в Китае.\n\n"
                f"⏰ *Требуется связаться в течение 15 минут!*"
            )
        else:
            notification_text = (
                f"📝 *НОВЫЙ ЗАПРОС - ТЕКСТ*\n\n"
                f"👤 Пользователь: {user_name} (@{username if username else 'без username'})\n"
                f"🆔 ID: `{user_id}`\n"
                f"📋 Заказ: `{order_id if order_id else 'N/A'}`\n\n"
                f"💬 Запрос: _{content[:200]}..._\n\n"
                f"⏰ *Требуется связаться в течение 15 минут!*"
            )
        
        # Отправляем уведомление менеджеру
        send_message(MANAGER_CHAT_ID, notification_text)
        logger.info(f"✅ Manager notified about request from user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to notify manager: {e}")
        return False

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
    try:
        logger.info("🚀 Starting BuyerChina Bot...")
        
        # Настраиваем webhook при запуске
        try:
            setup_webhook()
            logger.info("✅ Webhook setup completed")
        except Exception as e:
            logger.error(f"❌ Webhook setup failed: {e}")
        
        # Запускаем Flask приложение
        port = int(os.getenv('PORT', 5000))
        logger.info(f"🚀 Starting server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        logger.error(f"❌ Critical startup error: {e}")
        logger.info("🔄 Attempting minimal startup...")
        
        # Минимальный запуск без дополнительных функций
        port = int(os.getenv('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
