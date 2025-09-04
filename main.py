#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import json
from datetime import datetime
from flask import Flask, request, jsonify
import requests

# Google Sheets imports
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("Google Sheets libraries loaded successfully")
except ImportError as e:
    GOOGLE_SHEETS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Google Sheets libraries not available: {e}")

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
MANAGER_USERNAME = os.getenv('MANAGER_USERNAME', '@Dim_Shi')  # Username менеджера

# Google Sheets setup
google_sheets = None

def init_google_sheets():
    """Инициализация Google Sheets"""
    global google_sheets
    
    if not GOOGLE_SHEETS_AVAILABLE:
        logger.warning("Google Sheets libraries not available")
        return False
    
    try:
        # Получаем credentials из переменной окружения
        google_creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
        if not google_creds_json:
            logger.warning("GOOGLE_CREDENTIALS_JSON not found in environment")
            return False
        
        # Очищаем JSON от лишних символов и пробелов
        google_creds_json = google_creds_json.strip()
        if google_creds_json.startswith('"') and google_creds_json.endswith('"'):
            google_creds_json = google_creds_json[1:-1]
        
        # Заменяем экранированные кавычки
        google_creds_json = google_creds_json.replace('\\"', '"')
        google_creds_json = google_creds_json.replace('\\n', '\n')
        
        logger.info(f"JSON length: {len(google_creds_json)}, starts with: {google_creds_json[:50]}...")
        
        # Парсим JSON credentials
        creds_data = json.loads(google_creds_json)
        
        # Создаем credentials
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_info(creds_data, scopes=scope)
        gc = gspread.authorize(creds)
        
        # Открываем или создаем таблицу
        try:
            spreadsheet = gc.open("BuyerChina Orders Tracking")
            logger.info("✅ Connected to existing Google Sheets")
        except gspread.SpreadsheetNotFound:
            spreadsheet = gc.create("BuyerChina Orders Tracking")
            logger.info("✅ Created new Google Sheets")
            
            # Создаем листы
            try:
                spreadsheet.add_worksheet(title="Orders", rows="1000", cols="20")
                spreadsheet.add_worksheet(title="Users", rows="1000", cols="15") 
                spreadsheet.add_worksheet(title="Analytics", rows="1000", cols="10")
                
                # Добавляем заголовки для листа Orders
                orders_sheet = spreadsheet.worksheet("Orders")
                headers = [
                    "Timestamp", "User ID", "Username", "Product", "Description", 
                    "Price", "Supplier", "Status", "Order ID", "Notes"
                ]
                orders_sheet.append_row(headers)
                
                # Добавляем заголовки для листа Users
                users_sheet = spreadsheet.worksheet("Users")
                user_headers = [
                    "Timestamp", "User ID", "Username", "First Name", "Last Name",
                    "Language", "Action", "Message Type", "Content"
                ]
                users_sheet.append_row(user_headers)
                
                logger.info("✅ Created sheets with headers")
            except Exception as e:
                logger.error(f"Error creating sheets: {e}")
        
        google_sheets = spreadsheet
        logger.info("✅ Google Sheets initialized successfully")
        return True
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in GOOGLE_CREDENTIALS_JSON: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Google Sheets initialization failed: {e}")
        return False

def log_user_activity(user_id, username, first_name, last_name, language, action, message_type, content):
    """Логирование активности пользователя в Google Sheets"""
    if not google_sheets:
        logger.warning("Google Sheets not available for logging user activity")
        return False
    
    try:
        users_sheet = google_sheets.worksheet("Users")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row = [
            str(timestamp), str(user_id), str(username or ""), str(first_name or ""), str(last_name or ""),
            str(language or ""), str(action), str(message_type), str(content[:100] if content else "")
        ]
        
        users_sheet.append_row(row)
        logger.info(f"✅ Logged user activity: {user_id} - {action}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to log user activity: {e}")
        return False

def create_order(user_id, username, product, description, price, supplier):
    """Создание заказа в Google Sheets"""
    if not google_sheets:
        logger.warning("Google Sheets not available for creating order")
        return None
    
    try:
        orders_sheet = google_sheets.worksheet("Orders")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        order_id = f"ORD-{user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        row = [
            str(timestamp), str(user_id), str(username or ""), str(product), str(description),
            str(price), str(supplier), "New", str(order_id), ""
        ]
        
        orders_sheet.append_row(row)
        logger.info(f"✅ Created order: {order_id}")
        return order_id
        
    except Exception as e:
        logger.error(f"❌ Failed to create order: {e}")
        return None

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
                # Логируем активность пользователя
                log_user_activity(user_id, username, user_name, last_name, language, 
                                "start_command", "text", "/start")
                
                welcome_text = (
                    f"🇨🇳 *Добро пожаловать в BuyerChina, {user_name}!*\n\n"
                    "Ваш помощник для покупок в Китае.\n"
                    "Отправьте фото товара или его описание для поиска аналогов.\n\n"
                    "📊 Все ваши запросы сохраняются в Google Sheets для аналитики."
                )
                send_message(chat_id, welcome_text)
                
            elif 'photo' in message:
                # Логируем загрузку фото
                log_user_activity(user_id, username, user_name, last_name, language,
                                "photo_upload", "photo", "Photo uploaded for analysis")
                
                # Создаем заказ в Google Sheets
                order_id = create_order(user_id, username, "Photo Product", 
                                      "Product from uploaded photo", "$11.80", 
                                      "Shenzhen Manufacturer")
                
                # Уведомляем менеджера
                notify_manager(user_id, username, user_name, "photo", "Photo uploaded", order_id)
                
                response_text = (
                    f"📸 *Спасибо за фото, {user_name}!*\n\n"
                    "✅ *Ваша заявка принята в обработку*\n\n"
                    f"👨‍💼 Наш менеджер {MANAGER_USERNAME} уже получил уведомление и свяжется с вами в ближайшие *15 минут* или в удобное для вас время.\n\n"
                    "🔍 Мы найдем лучшие предложения от проверенных поставщиков в Китае:\n"
                    "• Анализ качества и цен\n"
                    "• Проверка надежности поставщика\n"
                    "• Помощь с доставкой и таможней\n\n"
                    f"📋 Номер заявки: `{order_id if order_id else 'N/A'}`\n\n"
                    "💬 Если у вас срочный вопрос, напишите {MANAGER_USERNAME} напрямую!"
                )
                send_message(chat_id, response_text)
                
            elif 'text' in message:
                text = message['text']
                
                # Логируем текстовый запрос
                log_user_activity(user_id, username, user_name, last_name, language,
                                "text_query", "text", text)
                
                # Создаем заказ для текстового запроса
                order_id = create_order(user_id, username, text, 
                                      f"Search query: {text}", "$8.90", 
                                      "Alibaba Supplier A")
                
                # Уведомляем менеджера
                notify_manager(user_id, username, user_name, "text", text, order_id)
                
                response_text = (
                    f"📝 *Спасибо за запрос, {user_name}!*\n\n"
                    f"💬 Ваш запрос: _{text}_\n\n"
                    "✅ *Заявка принята в обработку*\n\n"
                    f"👨‍💼 Наш менеджер {MANAGER_USERNAME} уже получил уведомление и свяжется с вами в ближайшие *15 минут* или в удобное для вас время.\n\n"
                    "🇨🇳 Мы найдем для вас:\n"
                    "• Лучшие цены от проверенных поставщиков\n"
                    "• Качественные аналоги товара\n"
                    "• Помощь с оформлением и доставкой\n"
                    "• Консультацию по таможенному оформлению\n\n"
                    f"📋 Номер заявки: `{order_id if order_id else 'N/A'}`\n\n"
                    f"💬 Для срочных вопросов пишите {MANAGER_USERNAME} напрямую!"
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

@app.route('/sheets_status')
def sheets_status():
    """Статус Google Sheets"""
    if google_sheets:
        try:
            sheet_url = f"https://docs.google.com/spreadsheets/d/{google_sheets.id}"
            return {
                "status": "connected",
                "sheet_id": google_sheets.id,
                "sheet_url": sheet_url,
                "title": google_sheets.title
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    else:
        return {"status": "not_connected", "message": "Google Sheets not initialized"}

@app.route('/test_sheets')
def test_sheets():
    """Тестирование записи в Google Sheets"""
    if not google_sheets:
        return {"error": "Google Sheets not connected"}
    
    try:
        # Тестируем запись в Users
        test_result = log_user_activity(
            user_id=1169659218,
            username="test_user", 
            first_name="Test",
            last_name="User",
            language="ru",
            action="test_action",
            message_type="test",
            content="Test message from /test_sheets endpoint"
        )
        
        # Тестируем создание заказа
        order_id = create_order(
            user_id=1169659218,
            username="test_user",
            product="Test Product",
            description="Test order from /test_sheets endpoint", 
            price="$10.00",
            supplier="Test Supplier"
        )
        
        return {
            "user_activity_logged": test_result,
            "order_created": order_id,
            "sheet_url": f"https://docs.google.com/spreadsheets/d/{google_sheets.id}"
        }
        
    except Exception as e:
        logger.error(f"Test sheets error: {e}")
        return {"error": str(e)}

if __name__ == '__main__':
    try:
        logger.info("🚀 Starting BuyerChina Bot with Google Sheets integration...")
        
        # Инициализируем Google Sheets
        try:
            if init_google_sheets():
                logger.info("✅ Google Sheets integration enabled")
            else:
                logger.warning("⚠️ Google Sheets integration disabled - continuing without it")
        except Exception as e:
            logger.error(f"❌ Google Sheets setup failed: {e}")
            logger.info("🔄 Continuing without Google Sheets...")
        
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
