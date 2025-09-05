#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import json
from flask import Flask, request, jsonify
import requests
import time

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
MANAGER_CHAT_ID = os.getenv('MANAGER_CHAT_ID', '1169659218')
logger.info(f"Manager chat ID: {MANAGER_CHAT_ID}")

def send_message(chat_id, text, parse_mode=None):
    """Отправка сообщений с обработкой ошибок"""
    try:
        url = f"{BOT_URL}/sendMessage"
        data = {
            'chat_id': str(chat_id),
            'text': text
        }
        if parse_mode:
            data['parse_mode'] = parse_mode
            
        response = requests.post(url, json=data, timeout=15)
        result = response.json()
        
        logger.info(f"Message sent to {chat_id}: Status {response.status_code}")
        
        if not result.get('ok'):
            logger.error(f"Telegram API error: {result}")
            
        return result
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
        'сколько стоит', 'где купить', 'как заказать', 'помогите найти', 'помочь найти'
    ]
    
    # Исключаем простые фразы
    exclude_phrases = [
        'привет', 'hello', 'hi', 'спасибо', 'thanks', 'ok', 'да', 'нет', 'yes', 'no',
        'хорошо', 'понятно', 'ясно', 'ок', 'окей', 'okay'
    ]
    
    text_lower = text.lower().strip()
    
    # Если это исключенная фраза
    if text_lower in exclude_phrases:
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
    """Уведомление менеджера с несколькими попытками"""
    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            logger.info(f"🔔 Attempt {attempt + 1}/{max_attempts} to notify manager {MANAGER_CHAT_ID}")
            
            # Простой текст без форматирования для надежности
            if message_type == "photo":
                notification_text = (
                    f"🚨 НОВЫЙ ЗАПРОС - ФОТО\n\n"
                    f"👤 Пользователь: {user_name}\n"
                    f"📱 Username: @{username if username else 'не указан'}\n"
                    f"🆔 ID: {user_id}\n\n"
                    f"📸 Пользователь загрузил фото товара для поиска аналогов в Китае.\n\n"
                    f"⏰ ТРЕБУЕТСЯ СВЯЗАТЬСЯ В ТЕЧЕНИЕ 15 МИНУТ!"
                )
            else:
                # Ограничиваем длину содержимого
                safe_content = content[:300] if len(content) > 300 else content
                notification_text = (
                    f"🚨 НОВЫЙ ЗАПРОС - ТЕКСТ\n\n"
                    f"👤 Пользователь: {user_name}\n"
                    f"📱 Username: @{username if username else 'не указан'}\n"
                    f"🆔 ID: {user_id}\n\n"
                    f"💬 Запрос: {safe_content}\n\n"
                    f"⏰ ТРЕБУЕТСЯ СВЯЗАТЬСЯ В ТЕЧЕНИЕ 15 МИНУТ!"
                )
            
            logger.info(f"📤 Sending notification to manager (attempt {attempt + 1})...")
            
            # Отправляем без форматирования
            result = send_message(MANAGER_CHAT_ID, notification_text)
            
            if result and result.get('ok'):
                logger.info(f"✅ Manager notification sent successfully to {MANAGER_CHAT_ID}")
                return True
            else:
                logger.error(f"❌ Failed to send notification (attempt {attempt + 1}): {result}")
                
                if attempt < max_attempts - 1:
                    time.sleep(1)  # Пауза перед повторной попыткой
                    continue
                else:
                    return False
        
        except Exception as e:
            logger.error(f"❌ Exception in notify_manager (attempt {attempt + 1}): {e}")
            if attempt < max_attempts - 1:
                time.sleep(1)
                continue
            else:
                return False
    
    return False

def test_manager_connection():
    """Тестирование соединения с менеджером"""
    try:
        logger.info(f"🧪 Testing connection to manager {MANAGER_CHAT_ID}")
        test_message = f"🧪 Тест связи с ботом - {time.strftime('%H:%M:%S')}\n\nЕсли вы получили это сообщение, уведомления работают правильно!"
        
        result = send_message(MANAGER_CHAT_ID, test_message)
        
        if result and result.get('ok'):
            logger.info("✅ Manager connection test successful")
            return True
        else:
            logger.error(f"❌ Manager connection test failed: {result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Manager connection test error: {e}")
        return False

def get_bot_info():
    """Получение информации о боте"""
    try:
        url = f"{BOT_URL}/getMe"
        response = requests.get(url, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Get bot info error: {e}")
        return None

def setup_webhook():
    """Настройка webhook"""
    try:
        # Получаем URL из переменных окружения
        railway_url = os.getenv('RAILWAY_PUBLIC_DOMAIN') or os.getenv('RAILWAY_STATIC_URL')
        
        if railway_url:
            if not railway_url.startswith('http'):
                webhook_url = f"https://{railway_url}/webhook"
            else:
                webhook_url = f"{railway_url}/webhook"
        else:
            # Используйте свой актуальный URL
            webhook_url = "https://web-production-ea35.up.railway.app/webhook"
            logger.warning(f"Using fallback webhook URL: {webhook_url}")
        
        logger.info(f"Setting webhook to: {webhook_url}")
        
        # Удаляем старый webhook
        delete_url = f"{BOT_URL}/deleteWebhook"
        requests.post(delete_url, timeout=10)
        logger.info("Old webhook deleted")
        
        # Устанавливаем новый webhook
        set_url = f"{BOT_URL}/setWebhook"
        data = {'url': webhook_url}
        response = requests.post(set_url, json=data, timeout=15)
        result = response.json()
        
        if result.get('ok'):
            logger.info(f"✅ Webhook set successfully: {webhook_url}")
            return True
        else:
            logger.error(f"❌ Webhook setup failed: {result}")
            return False
            
    except Exception as e:
        logger.error(f"Webhook setup error: {e}")
        return False

@app.route('/')
def health():
    """Проверка работы сервиса"""
    bot_info = get_bot_info()
    return jsonify({
        "status": "running",
        "bot": bot_info.get('result', {}).get('username', 'unknown') if bot_info else 'error',
        "manager_id": MANAGER_CHAT_ID,
        "message": "BuyerChina Bot is running!"
    }), 200

@app.route('/test_manager')
def test_manager():
    """Тест уведомления менеджера"""
    try:
        # Тестируем простое соединение
        connection_test = test_manager_connection()
        
        # Тестируем полное уведомление
        time.sleep(1)  # Пауза между сообщениями
        notification_test = notify_manager(
            user_id="TEST_USER_123",
            username="test_user", 
            user_name="Тестовый Пользователь",
            message_type="text",
            content="Это тестовое сообщение для проверки уведомлений менеджера. Если вы его видите - всё работает правильно!"
        )
        
        return jsonify({
            "connection_test": connection_test,
            "notification_test": notification_test,
            "manager_id": MANAGER_CHAT_ID,
            "status": "success" if (connection_test and notification_test) else "failed",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        logger.error(f"Test error: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500

@app.route('/set_webhook')
def manual_webhook():
    """Ручная установка webhook"""
    try:
        if setup_webhook():
            return "✅ Webhook set successfully!"
        else:
            return "❌ Webhook setup failed", 500
    except Exception as e:
        return f"❌ Error: {e}", 500

@app.route('/webhook_info')
def webhook_info():
    """Информация о webhook"""
    try:
        url = f"{BOT_URL}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/bot_info')
def bot_info():
    """Информация о боте"""
    try:
        info = get_bot_info()
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработка входящих сообщений"""
    try:
        data = request.get_json()
        
        if not data:
            logger.error("Empty request data")
            return "No data", 400
            
        logger.info(f"📨 Received update from Telegram")
        
        if 'message' not in data:
            logger.info("Update without message, skipping")
            return "OK", 200
            
        message = data['message']
        chat_id = message['chat']['id']
        user_data = message.get('from', {})
        user_id = user_data.get('id')
        user_name = user_data.get('first_name', 'Пользователь')
        username = user_data.get('username', '')
        
        logger.info(f"👤 Processing message from user: {user_name} (ID: {user_id})")
        
        # Команда /start
        if 'text' in message and message['text'] == '/start':
            welcome_text = (
                f"🇨🇳 Добро пожаловать в BuyerChina, {user_name}!\n\n"
                f"Ваш помощник для покупок в Китае.\n\n"
                f"Отправьте:\n"
                f"📸 Фото товара\n"
                f"📝 Описание того, что ищете\n\n"
                f"Наш менеджер свяжется с вами в течение 15 минут!"
            )
            send_message(chat_id, welcome_text)
            logger.info(f"📝 Sent welcome message to {user_name}")
            
        # Обработка фото
        elif 'photo' in message:
            logger.info(f"📸 Photo received from {user_name}, processing...")
            
            # Уведомляем менеджера
            notification_sent = notify_manager(user_id, username, user_name, "photo", "Фото для поиска товара")
            
            if notification_sent:
                logger.info("✅ Manager notified about photo")
            else:
                logger.error("❌ Failed to notify manager about photo")
            
            # Отвечаем пользователю
            response_text = (
                f"📸 Спасибо за фото, {user_name}!\n\n"
                f"✅ Ваша заявка принята в обработку.\n\n"
                f"👨‍💼 Наш менеджер уже получил уведомление и свяжется с вами в ближайшие 15 минут.\n\n"
                f"🔍 Мы найдем лучшие предложения от проверенных поставщиков в Китае!"
            )
            send_message(chat_id, response_text)
            
        # Обработка текста
        elif 'text' in message:
            text = message['text']
            
            # Пропускаем команды
            if text.startswith('/'):
                logger.info(f"Command received: {text}")
                return "OK", 200
            
            # Проверяем является ли это реальным заказом
            if is_real_order(text):
                logger.info(f"📝 Real order detected from {user_name}, processing...")
                
                # Уведомляем менеджера
                notification_sent = notify_manager(user_id, username, user_name, "text", text)
                
                if notification_sent:
                    logger.info("✅ Manager notified about text order")
                else:
                    logger.error("❌ Failed to notify manager about text order")
                
                # Отвечаем пользователю
                response_text = (
                    f"📝 Спасибо за запрос, {user_name}!\n\n"
                    f"💬 Ваш запрос: {text[:100]}{'...' if len(text) > 100 else ''}\n\n"
                    f"✅ Заявка принята в обработку.\n\n"
                    f"👨‍💼 Наш менеджер уже получил уведомление и свяжется с вами в ближайшие 15 минут."
                )
                send_message(chat_id, response_text)
                
            else:
                logger.info(f"💬 Regular message from {user_name}, sending help")
                # Простой ответ на обычные сообщения
                response_text = (
                    f"Привет, {user_name}! 👋\n\n"
                    f"Для поиска товаров в Китае:\n"
                    f"📸 Отправьте фото товара\n"
                    f"📝 Или опишите что ищете\n\n"
                    f"Например:\n"
                    f"• \"Хочу найти беспроводные наушники\"\n"
                    f"• \"Нужна куртка как на фото\"\n"
                    f"• \"Ищу телефон Samsung\""
                )
                send_message(chat_id, response_text)
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return "Error", 500

if __name__ == '__main__':
    try:
        logger.info("🚀 Starting BuyerChina Bot...")
        
        # Проверяем информацию о боте
        bot_info = get_bot_info()
        if bot_info and bot_info.get('ok'):
            bot_username = bot_info['result']['username']
            logger.info(f"✅ Bot info: @{bot_username}")
        else:
            logger.error("❌ Failed to get bot info - check BOT_TOKEN")
        
        # Тестируем соединение с менеджером
        logger.info("🧪 Testing manager connection on startup...")
        if test_manager_connection():
            logger.info("✅ Manager connection OK")
        else:
            logger.error("❌ Manager connection FAILED - check MANAGER_CHAT_ID")
        
        # Настраиваем webhook
        try:
            if setup_webhook():
                logger.info("✅ Webhook setup completed")
            else:
                logger.error("❌ Webhook setup failed")
        except Exception as e:
            logger.error(f"❌ Webhook setup error: {e}")
        
        # Запускаем сервер
        port = int(os.getenv('PORT', 5000))
        logger.info(f"🌐 Starting server on port {port}")
        
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        # Минимальный запуск в случае ошибки
        port = int(os.getenv('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)