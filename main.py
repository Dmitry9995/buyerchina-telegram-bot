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
    """Отправка сообщений с детальной диагностикой"""
    try:
        url = f"{BOT_URL}/sendMessage"
        data = {
            'chat_id': str(chat_id),
            'text': text
        }
        if parse_mode:
            data['parse_mode'] = parse_mode
        
        logger.info(f"Sending message to chat_id: {chat_id}")
        logger.info(f"Message text: {text[:100]}...")
        
        response = requests.post(url, json=data, timeout=15)
        result = response.json()
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {result}")
        
        return result
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return None

def is_real_order(text):
    """Проверка является ли сообщение реальным заказом"""
    if not text or len(text.strip()) < 5:
        return False
    
    order_keywords = [
        'купить', 'заказать', 'найти', 'нужно', 'хочу', 'ищу', 'товар', 'цена', 'стоимость',
        'доставка', 'китай', 'алиэкспресс', 'alibaba', 'taobao', '1688', 'dhgate',
        'сколько стоит', 'где купить', 'как заказать', 'помогите найти', 'помочь найти'
    ]
    
    exclude_phrases = [
        'привет', 'hello', 'hi', 'спасибо', 'thanks', 'ok', 'да', 'нет', 'yes', 'no',
        'хорошо', 'понятно', 'ясно', 'ок', 'окей', 'okay'
    ]
    
    text_lower = text.lower().strip()
    
    if text_lower in exclude_phrases:
        return False
    
    for keyword in order_keywords:
        if keyword in text_lower:
            return True
    
    if len(text.strip()) > 20:
        return True
    
    return False

def notify_manager(user_id, username, user_name, message_type, content):
    """Уведомление менеджера с детальной диагностикой"""
    try:
        logger.info(f"🔔 Starting notification process for manager {MANAGER_CHAT_ID}")
        
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
            safe_content = content[:300] if len(content) > 300 else content
            notification_text = (
                f"🚨 НОВЫЙ ЗАПРОС - ТЕКСТ\n\n"
                f"👤 Пользователь: {user_name}\n"
                f"📱 Username: @{username if username else 'не указан'}\n"
                f"🆔 ID: {user_id}\n\n"
                f"💬 Запрос: {safe_content}\n\n"
                f"⏰ ТРЕБУЕТСЯ СВЯЗАТЬСЯ В ТЕЧЕНИЕ 15 МИНУТ!"
            )
        
        logger.info("📤 Attempting to send notification to manager...")
        result = send_message(MANAGER_CHAT_ID, notification_text)
        
        if result and result.get('ok'):
            logger.info(f"✅ Manager notification sent successfully")
            return True
        else:
            logger.error(f"❌ Failed to send notification: {result}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Exception in notify_manager: {e}")
        return False

def get_chat_info(chat_id):
    """Получение информации о чате для диагностики"""
    try:
        url = f"{BOT_URL}/getChat"
        data = {'chat_id': str(chat_id)}
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        logger.info(f"Chat info for {chat_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Get chat info error: {e}")
        return None

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
        railway_url = os.getenv('RAILWAY_PUBLIC_DOMAIN') or os.getenv('RAILWAY_STATIC_URL')
        
        if railway_url:
            if not railway_url.startswith('http'):
                webhook_url = f"https://{railway_url}/webhook"
            else:
                webhook_url = f"{railway_url}/webhook"
        else:
            webhook_url = "https://web-production-ea35.up.railway.app/webhook"
            logger.warning(f"Using fallback webhook URL: {webhook_url}")
        
        logger.info(f"Setting webhook to: {webhook_url}")
        
        delete_url = f"{BOT_URL}/deleteWebhook"
        requests.post(delete_url, timeout=10)
        
        set_url = f"{BOT_URL}/setWebhook"
        data = {'url': webhook_url}
        response = requests.post(set_url, json=data, timeout=15)
        result = response.json()
        
        logger.info(f"Webhook setup result: {result}")
        return result.get('ok', False)
        
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

@app.route('/debug_manager')
def debug_manager():
    """Расширенная диагностика менеджера"""
    try:
        results = {}
        
        # 1. Проверяем информацию о чате менеджера
        logger.info(f"🔍 Getting chat info for manager {MANAGER_CHAT_ID}")
        chat_info = get_chat_info(MANAGER_CHAT_ID)
        results['chat_info'] = chat_info
        
        # 2. Пробуем отправить простое сообщение
        logger.info("📤 Attempting to send test message")
        test_message = f"🧪 ТЕСТ СОЕДИНЕНИЯ - {time.strftime('%H:%M:%S')}"
        send_result = send_message(MANAGER_CHAT_ID, test_message)
        results['send_test'] = send_result
        
        # 3. Пробуем отправить полное уведомление
        time.sleep(1)
        logger.info("📤 Attempting to send full notification")
        notification_result = notify_manager(
            user_id="DEBUG_123",
            username="debug_user",
            user_name="Отладочный Пользователь",
            message_type="text",
            content="Это отладочное сообщение для проверки системы уведомлений"
        )
        results['notification_test'] = notification_result
        
        return jsonify({
            "manager_id": MANAGER_CHAT_ID,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "tests": results,
            "status": "success" if results.get('send_test', {}).get('ok') else "failed"
        })
        
    except Exception as e:
        logger.error(f"Debug error: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500

@app.route('/find_chat_id')
def find_chat_id():
    """Помощь в поиске правильного chat_id"""
    try:
        # Получаем последние обновления
        url = f"{BOT_URL}/getUpdates"
        response = requests.get(url, timeout=10)
        result = response.json()
        
        if result.get('ok') and result.get('result'):
            chats = []
            for update in result['result'][-10:]:  # Последние 10 сообщений
                if 'message' in update:
                    msg = update['message']
                    chat_info = {
                        'chat_id': msg['chat']['id'],
                        'chat_type': msg['chat']['type'],
                        'user_name': msg.get('from', {}).get('first_name', 'Unknown'),
                        'username': msg.get('from', {}).get('username', ''),
                        'text': msg.get('text', msg.get('caption', 'No text'))[:50]
                    }
                    chats.append(chat_info)
            
            return jsonify({
                "status": "success",
                "recent_chats": chats,
                "current_manager_id": MANAGER_CHAT_ID,
                "instructions": "Найдите ваш chat_id в списке и обновите переменную MANAGER_CHAT_ID"
            })
        else:
            return jsonify({
                "status": "no_updates",
                "message": "Нет недавних сообщений. Отправьте сообщение боту и попробуйте снова."
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/test_chat_id/<chat_id>')
def test_chat_id(chat_id):
    """Тест отправки сообщения в конкретный chat_id"""
    try:
        test_message = f"🧪 Тест отправки в чат {chat_id} - {time.strftime('%H:%M:%S')}"
        result = send_message(chat_id, test_message)
        
        return jsonify({
            "chat_id": chat_id,
            "result": result,
            "success": result.get('ok', False) if result else False
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/webhook_info')
def webhook_info():
    """Информация о webhook"""
    try:
        url = f"{BOT_URL}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработка входящих сообщений"""
    try:
        data = request.get_json()
        
        if not data:
            logger.error("Empty request data")
            return "No data", 400
            
        logger.info(f"📨 Received update: {json.dumps(data, ensure_ascii=False)}")
        
        if 'message' not in data:
            return "OK", 200
            
        message = data['message']
        chat_id = message['chat']['id']
        user_data = message.get('from', {})
        user_id = user_data.get('id')
        user_name = user_data.get('first_name', 'Пользователь')
        username = user_data.get('username', '')
        
        logger.info(f"👤 Processing message from: {user_name} (ID: {user_id}, Chat: {chat_id})")
        
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
            
        # Обработка фото
        elif 'photo' in message:
            logger.info(f"📸 Photo received from {user_name}")
            
            notification_sent = notify_manager(user_id, username, user_name, "photo", "Фото для поиска товара")
            
            response_text = (
                f"📸 Спасибо за фото, {user_name}!\n\n"
                f"✅ Ваша заявка принята в обработку.\n\n"
                f"👨‍💼 Наш менеджер {'уже получил уведомление' if notification_sent else 'получит уведомление'} и свяжется с вами в ближайшие 15 минут."
            )
            send_message(chat_id, response_text)
            
        # Обработка текста
        elif 'text' in message:
            text = message['text']
            
            if text.startswith('/'):
                return "OK", 200
            
            if is_real_order(text):
                logger.info(f"📝 Real order detected from {user_name}")
                
                notification_sent = notify_manager(user_id, username, user_name, "text", text)
                
                response_text = (
                    f"📝 Спасибо за запрос, {user_name}!\n\n"
                    f"💬 Ваш запрос: {text[:100]}{'...' if len(text) > 100 else ''}\n\n"
                    f"✅ Заявка принята в обработку.\n\n"
                    f"👨‍💼 Наш менеджер {'уже получил уведомление' if notification_sent else 'получит уведомление'} и свяжется с вами в ближайшие 15 минут."
                )
                send_message(chat_id, response_text)
                
            else:
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
        port = int(os.getenv('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)