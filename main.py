#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from flask import Flask, request
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

def send_message(chat_id, text):
    try:
        url = f"{BOT_URL}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text
        }
        response = requests.post(url, json=data, timeout=10)
        logger.info(f"Message sent to {chat_id}: {response.status_code}")
        return response.json()
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return None

def is_real_order(text):
    """Проверка является ли сообщение реальным заказом"""
    if not text or len(text.strip()) < 5:
        return False
    
    # Ключевые слова для заказов
    order_keywords = [
        'купить', 'заказать', 'найти', 'нужно', 'хочу', 'ищу', 'товар', 'цена', 'стоимость',
        'доставка', 'китай', 'алиэкспресс', 'alibaba', 'taobao', '1688', 'dhgate',
        'сколько стоит', 'где купить', 'как заказать', 'помогите найти'
    ]
    
    # Исключаем простые фразы
    exclude_phrases = [
        'привет', 'hello', 'hi', 'спасибо', 'thanks', 'ok', 'да', 'нет', 'yes', 'no',
        'хорошо', 'понятно', 'ясно', 'ок', 'окей', 'okay'
    ]
    
    text_lower = text.lower().strip()
    
    # Если это исключенная фраза
    if text_lower in exclude_phrases or len(text_lower) < 5:
        return False
    
    # Если содержит ключевые слова заказа
    for keyword in order_keywords:
        if keyword in text_lower:
            return True
    
    # Если длинное сообщение (вероятно описание товара)
    if len(text.strip()) > 20:
        return True
    
    return False

def notify_manager(user_id, username, user_name, message_type, content):
    """Уведомление менеджера о новом запросе"""
    try:
        logger.info(f"🔔 Attempting to notify manager {MANAGER_CHAT_ID}")
        
        if message_type == "photo":
            notification_text = (
                f"📸 НОВЫЙ ЗАПРОС - ФОТО\n\n"
                f"👤 Пользователь: {user_name} (@{username if username else 'без username'})\n"
                f"🆔 ID: {user_id}\n\n"
                f"📝 Пользователь загрузил фото товара для поиска аналогов в Китае.\n\n"
                f"⏰ Требуется связаться в течение 15 минут!"
            )
        else:
            notification_text = (
                f"📝 НОВЫЙ ЗАПРОС - ТЕКСТ\n\n"
                f"👤 Пользователь: {user_name} (@{username if username else 'без username'})\n"
                f"🆔 ID: {user_id}\n\n"
                f"💬 Запрос: {content}\n\n"
                f"⏰ Требуется связаться в течение 15 минут!"
            )
        
        logger.info(f"📤 Sending notification to manager: {notification_text[:100]}...")
        
        # Отправляем уведомление менеджеру напрямую через API
        try:
            url = f"{BOT_URL}/sendMessage"
            data = {
                'chat_id': str(MANAGER_CHAT_ID),
                'text': notification_text
            }
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            logger.info(f"📊 Manager notification response: {result}")
            
            if response.status_code == 200 and result.get('ok'):
                logger.info(f"✅ Manager notification sent successfully to {MANAGER_CHAT_ID}")
                return True
            else:
                logger.error(f"❌ Failed to send notification: {result}")
                return False
                
        except Exception as api_error:
            logger.error(f"❌ API error sending to manager: {api_error}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Exception in notify_manager: {e}")
        return False

def setup_webhook():
    """Setup webhook for Railway"""
    try:
        railway_url = os.getenv('RAILWAY_PUBLIC_DOMAIN')
        if railway_url:
            webhook_url = f"https://{railway_url}/webhook"
        else:
            webhook_url = f"https://web-production-ea35.up.railway.app/webhook"
        
        delete_url = f"{BOT_URL}/deleteWebhook"
        requests.post(delete_url, timeout=10)
        
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
    return "BuyerChina Bot is running!", 200

@app.route('/test_manager')
def test_manager():
    """Тест уведомления менеджера"""
    try:
        test_result = notify_manager(
            user_id="TEST123",
            username="testuser", 
            user_name="Тестовый пользователь",
            message_type="text",
            content="Тестовое сообщение для проверки уведомлений"
        )
        if test_result:
            return f"✅ Тест успешен! Уведомление отправлено менеджеру {MANAGER_CHAT_ID}"
        else:
            return "❌ Ошибка отправки уведомления"
    except Exception as e:
        return f"❌ Ошибка теста: {e}"

@app.route('/set_webhook')
def manual_webhook():
    """Manual webhook setup"""
    if setup_webhook():
        return "✅ Webhook set successfully!"
    else:
        return "❌ Webhook setup failed"

@app.route('/webhook_info')
def webhook_info():
    """Get webhook info"""
    try:
        url = f"{BOT_URL}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

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
            
            if 'text' in message and message['text'] == '/start':
                welcome_text = f"🇨🇳 Добро пожаловать в BuyerChina, {user_name}!\n\nВаш помощник для покупок в Китае.\nОтправьте фото товара или его описание для поиска аналогов."
                send_message(chat_id, welcome_text)
                
            elif 'photo' in message:
                # Уведомляем менеджера
                notify_manager(user_id, username, user_name, "photo", "Фото загружено")
                
                response_text = f"📸 Спасибо за фото, {user_name}!\n\n✅ Ваша заявка принята в обработку.\n\n👨‍💼 Наш менеджер уже получил уведомление и свяжется с вами в ближайшие 15 минут.\n\n🔍 Мы найдем лучшие предложения от проверенных поставщиков в Китае!"
                send_message(chat_id, response_text)
                
            elif 'text' in message:
                text = message['text']
                if text != '/start':  # Не уведомляем о команде /start
                    # Проверяем является ли это реальным заказом
                    if is_real_order(text):
                        # Уведомляем менеджера только для реальных заказов
                        notify_manager(user_id, username, user_name, "text", text)
                        
                        response_text = f"📝 Спасибо за запрос, {user_name}!\n\n💬 Ваш запрос: {text}\n\n✅ Заявка принята в обработку.\n\n👨‍💼 Наш менеджер уже получил уведомление и свяжется с вами в ближайшие 15 минут."
                        send_message(chat_id, response_text)
                    else:
                        # Простой ответ на обычные сообщения
                        response_text = f"Привет, {user_name}! 👋\n\nДля поиска товаров в Китае:\n📸 Отправьте фото товара\n📝 Или опишите что ищете\n\nНапример: \"Хочу найти беспроводные наушники\" или \"Нужна куртка как на фото\""
                        send_message(chat_id, response_text)
        
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

if __name__ == '__main__':
    try:
        logger.info("🚀 Starting BuyerChina Bot...")
        
        # Setup webhook on startup
        try:
            setup_webhook()
            logger.info("✅ Webhook setup completed")
        except Exception as e:
            logger.error(f"❌ Webhook setup failed: {e}")
        
        port = int(os.getenv('PORT', 5000))
        logger.info(f"Starting server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        logger.error(f"Startup error: {e}")
        # Minimal startup fallback
        port = int(os.getenv('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
