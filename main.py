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
        
    except Exception as e:
        logger.error(f"Google Sheets initialization failed: {e}")
        return False

def log_user_activity(user_id, username, first_name, last_name, language, action, message_type, content):
    """Логирование активности пользователя в Google Sheets"""
    if not google_sheets:
        return False
    
    try:
        users_sheet = google_sheets.worksheet("Users")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row = [
            timestamp, user_id, username or "", first_name or "", last_name or "",
            language or "", action, message_type, content[:100] if content else ""
        ]
        
        users_sheet.append_row(row)
        logger.info(f"✅ Logged user activity: {user_id} - {action}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to log user activity: {e}")
        return False

def create_order(user_id, username, product, description, price, supplier):
    """Создание заказа в Google Sheets"""
    if not google_sheets:
        return False
    
    try:
        orders_sheet = google_sheets.worksheet("Orders")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        order_id = f"ORD-{user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        row = [
            timestamp, user_id, username or "", product, description,
            price, supplier, "New", order_id, ""
        ]
        
        orders_sheet.append_row(row)
        logger.info(f"✅ Created order: {order_id}")
        return order_id
        
    except Exception as e:
        logger.error(f"Failed to create order: {e}")
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
                
                response_text = (
                    f"📸 *Получил фото от {user_name}!*\n\n"
                    "🔍 Анализирую изображение...\n"
                    "🇨🇳 Ищу аналогичные товары в Китае...\n"
                    "💰 Сравниваю цены у разных поставщиков...\n\n"
                    "*Примерные результаты:*\n"
                    "🏭 Поставщик 1: Guangzhou Factory - $12.50\n"
                    "🏭 Поставщик 2: Shenzhen Manufacturer - $11.80\n"
                    "🏭 Поставщик 3: Yiwu Supplier - $13.20\n\n"
                    "✅ Рекомендуем: Shenzhen Manufacturer (лучшая цена)\n\n"
                    f"📋 Заказ создан: `{order_id if order_id else 'N/A'}`"
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
                
                response_text = (
                    f"📝 *Получил запрос:* {text}\n\n"
                    "🔍 Ищу товары в базе китайских поставщиков...\n"
                    "💰 Анализирую цены и качество...\n\n"
                    "*Найденные товары:*\n"
                    "🏭 Alibaba Supplier A - $8.90 (MOQ: 100)\n"
                    "🏭 Made-in-China Supplier B - $9.50 (MOQ: 50)\n"
                    "🏭 DHgate Supplier C - $12.00 (MOQ: 1)\n\n"
                    "✅ Рекомендуем: Supplier A (лучшее соотношение цена/качество)\n\n"
                    f"📋 Заказ создан: `{order_id if order_id else 'N/A'}`"
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

if __name__ == '__main__':
    logger.info("🚀 Starting BuyerChina Bot with Google Sheets integration...")
    
    # Инициализируем Google Sheets
    if init_google_sheets():
        logger.info("✅ Google Sheets integration enabled")
    else:
        logger.warning("⚠️ Google Sheets integration disabled")
    
    # Настраиваем webhook при запуске
    setup_webhook()
    
    # Запускаем Flask приложение
    port = int(os.getenv('PORT', 5000))
    logger.info(f"🚀 Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
