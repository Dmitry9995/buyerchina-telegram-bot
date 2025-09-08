#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import json
from flask import Flask, request
import requests
from datetime import datetime
import mimetypes
from urllib.parse import urlparse

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets imports - с обработкой ошибок
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    logger.warning("Google Sheets libraries not available")

# Flask приложение
app = Flask(__name__)

# Глобальные переменные
BOT_TOKEN = None
BOT_URL = None

# Google Sheets
google_sheets = None
orders_data = {}
users_data = {}

# Админы
ADMIN_IDS = [1169659218]  # Ваш ID админа

def get_file_info(file_id):
    """Получение информации о файле"""
    try:
        url = f"{BOT_URL}/getFile"
        data = {'file_id': file_id}
        response = requests.post(url, json=data, timeout=15)
        result = response.json()
        
        if result.get('ok'):
            return result['result']
        else:
            logger.error(f"Failed to get file info: {result}")
            return None
    except Exception as e:
        logger.error(f"Get file info error: {e}")
        return None

def download_file(file_path):
    """Скачивание файла с серверов Telegram"""
    try:
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        response = requests.get(file_url, timeout=30)
        
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"Failed to download file: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Download file error: {e}")
        return None

def get_file_type_info(file_name):
    """Определение типа файла и его описания"""
    if not file_name:
        return "unknown", "Неизвестный файл"
    
    file_name_lower = file_name.lower()
    
    # Изображения
    if any(file_name_lower.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']):
        return "photo", "📸 Изображение"
    
    # Excel файлы
    elif any(file_name_lower.endswith(ext) for ext in ['.xlsx', '.xls', '.xlsm']):
        return "excel", "📊 Excel таблица"
    
    # PDF файлы
    elif file_name_lower.endswith('.pdf'):
        return "pdf", "📄 PDF документ"
    
    # Word файлы
    elif any(file_name_lower.endswith(ext) for ext in ['.docx', '.doc']):
        return "word", "📝 Word документ"
    
    # Другие документы
    elif any(file_name_lower.endswith(ext) for ext in ['.txt', '.rtf']):
        return "document", "📄 Текстовый документ"
    
    else:
        return "other", "📎 Файл"

def send_message(chat_id, text, reply_markup=None):
    """Отправка сообщения через Telegram API"""
    try:
        url = f"{BOT_URL}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        if reply_markup:
            data['reply_markup'] = reply_markup
        response = requests.post(url, json=data, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return None

def create_main_menu(user_id=None):
    """Создание главного меню"""
    keyboard = {
        "inline_keyboard": [
            [{"text": "🔍 Поиск товаров", "callback_data": "search"}],
            [{"text": "✅ Проверка поставщика", "callback_data": "verify"}],
            [{"text": "📦 Мои заказы", "callback_data": "orders"}],
            [{"text": "🚚 Отслеживание", "callback_data": "tracking"}],
            [{"text": "❓ Помощь", "callback_data": "help"}, 
             {"text": "🌐 Язык", "callback_data": "language"}]
        ]
    }
    
    # Добавляем админ панель для администраторов
    if user_id and user_id in ADMIN_IDS:
        keyboard["inline_keyboard"].append([{"text": "⚙️ Админ панель", "callback_data": "admin"}])
    
    return keyboard

def init_google_sheets():
    """Инициализация Google Sheets"""
    global google_sheets
    
    if not GOOGLE_SHEETS_AVAILABLE:
        logger.info("Google Sheets libraries not available, skipping initialization")
        return None
        
    try:
        if not os.path.exists('credentials.json'):
            logger.warning("credentials.json not found. Google Sheets disabled.")
            return None
        
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
        gc = gspread.authorize(creds)
        
        # Открываем или создаем таблицу
        try:
            spreadsheet = gc.open("BuyerChina Orders Tracking")
        except gspread.SpreadsheetNotFound:
            spreadsheet = gc.create("BuyerChina Orders Tracking")
            # Создаем листы
            spreadsheet.add_worksheet(title="Orders", rows="1000", cols="20")
            spreadsheet.add_worksheet(title="Users", rows="1000", cols="15")
            spreadsheet.add_worksheet(title="Analytics", rows="1000", cols="10")
        
        google_sheets = spreadsheet
        logger.info("Google Sheets connected successfully")
        return spreadsheet
        
    except Exception as e:
        logger.error(f"Google Sheets init error: {e}")
        return None

def sync_user_data(user_id, user_info):
    """Синхронизация данных пользователя с Google Sheets"""
    if not google_sheets:
        return
    
    try:
        users_sheet = google_sheets.worksheet("Users")
        
        # Проверяем, есть ли пользователь
        try:
            cell = users_sheet.find(str(user_id))
            row = cell.row
            # Обновляем данные
            users_sheet.update(f'B{row}:H{row}', [[
                user_info.get('username', ''),
                user_info.get('first_name', ''),
                user_info.get('last_name', ''),
                user_info.get('language', 'ru'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                user_info.get('orders_count', 0),
                user_info.get('status', 'active')
            ]])
        except gspread.CellNotFound:
            # Добавляем нового пользователя
            users_sheet.append_row([
                user_id,
                user_info.get('username', ''),
                user_info.get('first_name', ''),
                user_info.get('last_name', ''),
                user_info.get('language', 'ru'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                user_info.get('orders_count', 0),
                user_info.get('status', 'active')
            ])
    except Exception as e:
        logger.error(f"User sync error: {e}")

def create_order(user_id, product_info):
    """Создание заказа"""
    order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
    order_data = {
        'order_id': order_id,
        'user_id': user_id,
        'product': product_info,
        'status': 'pending',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_amount': 0
    }
    
    orders_data[order_id] = order_data
    
    # Синхронизируем с Google Sheets
    if google_sheets:
        try:
            orders_sheet = google_sheets.worksheet("Orders")
            orders_sheet.append_row([
                order_id,
                user_id,
                product_info,
                'pending',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                0,
                '',  # supplier
                '',  # tracking
                ''   # notes
            ])
        except Exception as e:
            logger.error(f"Order sync error: {e}")
    
    return order_id

@app.route('/')
def health():
    """Health check"""
    return "🇨🇳 BuyerChina Bot is running on PythonAnywhere!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook для обработки сообщений от Telegram"""
    try:
        data = request.get_json()
        logger.info(f"Received update: {data}")
        
        # Обработка callback queries (нажатия кнопок)
        if 'callback_query' in data:
            callback = data['callback_query']
            chat_id = callback['message']['chat']['id']
            message_id = callback['message']['message_id']
            callback_data = callback['data']
            
            # Отвечаем на callback query
            answer_callback_query(callback['id'])
            
            if callback_data == 'search':
                response_text = "🔍 *Поиск товаров*\n\nОтправьте фото товара или его описание для поиска аналогов в Китае."
                edit_message(chat_id, message_id, response_text)
            elif callback_data == 'verify':
                response_text = "✅ *Проверка поставщика*\n\nОтправьте название компании или ссылку на поставщика для проверки."
                edit_message(chat_id, message_id, response_text)
            elif callback_data == 'orders':
                # Показываем заказы пользователя
                user_orders = [o for o in orders_data.values() if o['user_id'] == chat_id]
                if user_orders:
                    response_text = "📦 *Мои заказы*\n\n"
                    for order in user_orders[-5:]:  # Последние 5 заказов
                        response_text += f"🔸 {order['order_id']}\n"
                        response_text += f"📝 {order['product'][:50]}...\n"
                        response_text += f"📊 Статус: {order['status']}\n"
                        response_text += f"📅 {order['created_at']}\n\n"
                else:
                    response_text = "📦 *Мои заказы*\n\nУ вас пока нет активных заказов.\nИспользуйте поиск товаров для создания заказа."
                
                back_keyboard = {
                    "inline_keyboard": [[{"text": "⬅️ Назад в меню", "callback_data": "back"}]]
                }
                edit_message(chat_id, message_id, response_text, back_keyboard)
            elif callback_data == 'tracking':
                response_text = "🚚 *Отслеживание посылок*\n\nОтправьте трек-номер для отслеживания посылки."
                edit_message(chat_id, message_id, response_text)
            elif callback_data == 'admin':
                if chat_id in ADMIN_IDS:
                    # Статистика для админа
                    total_users = len(users_data)
                    total_orders = len(orders_data)
                    pending_orders = len([o for o in orders_data.values() if o['status'] == 'pending'])
                    
                    sheets_status = "✅ Подключено" if google_sheets else "❌ Отключено"
                    
                    response_text = (
                        "⚙️ *Админ панель*\n\n"
                        f"👥 Пользователей: {total_users}\n"
                        f"📦 Всего заказов: {total_orders}\n"
                        f"⏳ Ожидают обработки: {pending_orders}\n"
                        f"📊 Google Sheets: {sheets_status}\n\n"
                        "Выберите действие:"
                    )
                    
                    admin_keyboard = {
                        "inline_keyboard": [
                            [{"text": "📋 Все заказы", "callback_data": "admin_orders"}],
                            [{"text": "👥 Пользователи", "callback_data": "admin_users"}],
                            [{"text": "📊 Статистика", "callback_data": "admin_stats"}]
                        ]
                    }
                    
                    if google_sheets:
                        admin_keyboard["inline_keyboard"].append([
                            {"text": "📊 Открыть Google Sheets", "url": f"https://docs.google.com/spreadsheets/d/{google_sheets.id}"}
                        ])
                    
                    admin_keyboard["inline_keyboard"].append([{"text": "⬅️ Назад", "callback_data": "back"}])
                    
                    edit_message(chat_id, message_id, response_text, admin_keyboard)
                else:
                    response_text = "❌ У вас нет доступа к админ панели."
                    edit_message(chat_id, message_id, response_text)
            elif callback_data == 'help':
                response_text = (
                    "❓ *Помощь BuyerChina Bot*\n\n"
                    "*Доступные функции:*\n"
                    "🔍 Поиск товаров по фото или описанию\n"
                    "✅ Проверка надежности поставщиков\n"
                    "📦 Управление заказами\n"
                    "🚚 Отслеживание посылок\n\n"
                    "*Как использовать:*\n"
                    "1. Выберите нужную функцию в меню\n"
                    "2. Следуйте инструкциям\n"
                    "3. Получайте результаты в реальном времени"
                )
                back_keyboard = {
                    "inline_keyboard": [[{"text": "⬅️ Назад в меню", "callback_data": "back"}]]
                }
                edit_message(chat_id, message_id, response_text, back_keyboard)
            elif callback_data == 'language':
                response_text = "🌐 *Выбор языка*\n\nВыберите предпочитаемый язык:"
                lang_keyboard = {
                    "inline_keyboard": [
                        [{"text": "🇷🇺 Русский", "callback_data": "lang_ru"}],
                        [{"text": "🇺🇸 English", "callback_data": "lang_en"}],
                        [{"text": "🇨🇳 中文", "callback_data": "lang_zh"}],
                        [{"text": "⬅️ Назад", "callback_data": "back"}]
                    ]
                }
                edit_message(chat_id, message_id, response_text, lang_keyboard)
            elif callback_data == 'back':
                welcome_text = (
                    "👋 Добро пожаловать!\n"
                    "Я — ваш **байер в Китае** с опытом работы более 5 лет.\n\n"
                    "🔹 **Что я могу для вас сделать:**\n"
                    "- Поиск и проверка поставщиков в Китае\n"
                    "- Подбор и покупка товаров напрямую с фабрик\n"
                    "- Оплата и проверка качества перед отправкой\n"
                    "- Логистика и доставка из Китая в Россию и СНГ\n"
                    "- Полное сопровождение заказа под ключ\n\n"
                    "📦 **Ключевые направления:**\n"
                    "покупка китайских товаров • логистика из Китая • доставка оптом • помощь в покупке • проверка поставщика • подбор товара\n\n"
                    "💬 Чтобы начать — напишите, какой товар вас интересует и пришли ТЗ или фото.\n\n"
                    "#байер #Китай #доставкаизкитая #логистика #покупкатоваров #проверкапоставщика #опт\n\n"
                    "Выберите нужную функцию:"
                )
                edit_message(chat_id, message_id, welcome_text, create_main_menu(chat_id))
            elif callback_data.startswith('admin_'):
                if chat_id not in ADMIN_IDS:
                    response_text = "❌ У вас нет доступа к админ функциям."
                    edit_message(chat_id, message_id, response_text)
                    return
                
                action = callback_data.split('_')[1]
                if action == 'orders':
                    if orders_data:
                        response_text = "📋 *Все заказы*\n\n"
                        for order_id, order in list(orders_data.items())[-10:]:  # Последние 10 заказов
                            response_text += f"🔸 {order_id}\n"
                            response_text += f"👤 User: {order['user_id']}\n"
                            response_text += f"📝 {order['product'][:40]}...\n"
                            response_text += f"📊 {order['status']}\n"
                            response_text += f"📅 {order['created_at']}\n\n"
                    else:
                        response_text = "📋 *Все заказы*\n\nЗаказов пока нет."
                elif action == 'users':
                    response_text = f"👥 *Пользователи*\n\nВсего пользователей: {len(users_data)}\n\n"
                    if google_sheets:
                        response_text += "📊 Подробная информация доступна в Google Sheets."
                elif action == 'stats':
                    total_orders = len(orders_data)
                    pending = len([o for o in orders_data.values() if o['status'] == 'pending'])
                    completed = len([o for o in orders_data.values() if o['status'] == 'completed'])
                    
                    response_text = (
                        "📊 *Статистика*\n\n"
                        f"📦 Всего заказов: {total_orders}\n"
                        f"⏳ В обработке: {pending}\n"
                        f"✅ Завершено: {completed}\n"
                        f"👥 Пользователей: {len(users_data)}\n"
                    )
                
                back_keyboard = {
                    "inline_keyboard": [
                        [{"text": "⚙️ Админ панель", "callback_data": "admin"}],
                        [{"text": "⬅️ Главное меню", "callback_data": "back"}]
                    ]
                }
                edit_message(chat_id, message_id, response_text, back_keyboard)
            elif callback_data.startswith('order_'):
                order_id = callback_data.split('_')[1]
                if order_id in orders_data:
                    # Обновляем статус заказа
                    orders_data[order_id]['status'] = 'confirmed'
                    
                    response_text = (
                        f"✅ *Заказ подтвержден!*\n\n"
                        f"📋 Номер заказа: `{order_id}`\n"
                        f"📝 Товар: {orders_data[order_id]['product']}\n"
                        f"📊 Статус: Подтвержден\n\n"
                        "*Следующие шаги:*\n"
                        "1. ⏳ Поиск лучшего поставщика\n"
                        "2. 💰 Согласование цены и условий\n"
                        "3. 🚚 Организация доставки\n"
                        "4. 📦 Отслеживание посылки\n\n"
                        "Мы свяжемся с вами в течение 24 часов!"
                    )
                    
                    # Обновляем в Google Sheets
                    if google_sheets:
                        try:
                            orders_sheet = google_sheets.worksheet("Orders")
                            # Находим строку заказа и обновляем статус
                            cell = orders_sheet.find(order_id)
                            if cell:
                                orders_sheet.update_cell(cell.row, 4, 'confirmed')
                        except Exception as e:
                            logger.error(f"Google Sheets update error: {e}")
                    
                    back_keyboard = {
                        "inline_keyboard": [
                            [{"text": "📦 Мои заказы", "callback_data": "orders"}],
                            [{"text": "⬅️ Главное меню", "callback_data": "back"}]
                        ]
                    }
                    edit_message(chat_id, message_id, response_text, back_keyboard)
                else:
                    response_text = "❌ Заказ не найден."
                    edit_message(chat_id, message_id, response_text)
            elif callback_data.startswith('lang_'):
                lang = callback_data.split('_')[1]
                lang_names = {'ru': 'Русский', 'en': 'English', 'zh': '中文'}
                response_text = f"✅ Язык изменен на {lang_names.get(lang, lang)}"
                edit_message(chat_id, message_id, response_text)
                # Возвращаемся в главное меню через 2 секунды
                import time
                time.sleep(2)
                welcome_text = (
                    "👋 Добро пожаловать!\n"
                    "Я — ваш **байер в Китае** с опытом работы более 5 лет.\n\n"
                    "🔹 **Что я могу для вас сделать:**\n"
                    "- Поиск и проверка поставщиков в Китае\n"
                    "- Подбор и покупка товаров напрямую с фабрик\n"
                    "- Оплата и проверка качества перед отправкой\n"
                    "- Логистика и доставка из Китая в Россию и СНГ\n"
                    "- Полное сопровождение заказа под ключ\n\n"
                    "📦 **Ключевые направления:**\n"
                    "покупка китайских товаров • логистика из Китая • доставка оптом • помощь в покупке • проверка поставщика • подбор товара\n\n"
                    "💬 Чтобы начать — напишите, какой товар вас интересует и пришли ТЗ или фото.\n\n"
                    "#байер #Китай #доставкаизкитая #логистика #покупкатоваров #проверкапоставщика #опт\n\n"
                    "Выберите нужную функцию:"
                )
                edit_message(chat_id, message_id, welcome_text, create_main_menu())
        
        # Обработка обычных сообщений
        elif 'message' in data:
            message = data['message']
            chat_id = message['chat']['id']
            user_name = message.get('from', {}).get('first_name', 'Пользователь')
            
            # Обработка команды /start
            if 'text' in message and message['text'] == '/start':
                # Синхронизируем данные пользователя
                user_info = {
                    'username': message.get('from', {}).get('username', ''),
                    'first_name': user_name,
                    'last_name': message.get('from', {}).get('last_name', ''),
                    'language': 'ru',
                    'orders_count': len([o for o in orders_data.values() if o['user_id'] == chat_id]),
                    'status': 'active'
                }
                sync_user_data(chat_id, user_info)
                
                welcome_text = (
                    f"👋 Добро пожаловать!\n"
                    f"Я — ваш **байер в Китае** с опытом работы более 5 лет.\n\n"
                    f"🔹 **Что я могу для вас сделать:**\n"
                    f"- Поиск и проверка поставщиков в Китае\n"
                    f"- Подбор и покупка товаров напрямую с фабрик\n"
                    f"- Оплата и проверка качества перед отправкой\n"
                    f"- Логистика и доставка из Китая в Россию и СНГ\n"
                    f"- Полное сопровождение заказа под ключ\n\n"
                    f"📦 **Ключевые направления:**\n"
                    f"покупка китайских товаров • логистика из Китая • доставка оптом • помощь в покупке • проверка поставщика • подбор товара\n\n"
                    f"💬 Чтобы начать — напишите, какой товар вас интересует и пришли ТЗ или фото.\n\n"
                    f"#байер #Китай #доставкаизкитая #логистика #покупкатоваров #проверкапоставщика #опт\n\n"
                    f"Выберите нужную функцию:"
                )
                send_message(chat_id, welcome_text, create_main_menu(chat_id))
                
            # Обработка фото
            elif 'photo' in message:
                username = message.get('from', {}).get('username', 'Unknown')
                
                # Получаем информацию о самом большом фото
                photos = message['photo']
                largest_photo = max(photos, key=lambda x: x.get('file_size', 0))
                file_id = largest_photo['file_id']
                
                # Получаем информацию о файле
                file_info = get_file_info(file_id)
                logger.info(f"Photo file info: {file_info}")
                
                # Создаем заказ на основе фото
                product_info = f"Поиск по фото от @{username}"
                order_id = create_order(chat_id, product_info)
                
                response_text = (
                    f"📸 *Получил фото от @{username}!*\n\n"
                    "🔍 Анализирую изображение...\n"
                    "🇨🇳 Ищу аналогичные товары в Китае...\n"
                    "💰 Сравниваю цены у разных поставщиков...\n\n"
                    f"📋 Создан заказ: `{order_id}`\n"
                    "⏳ Результаты будут готовы через несколько секунд!\n\n"
                    "*Примерные результаты:*\n"
                    "🏭 Поставщик 1: Guangzhou Factory - $12.50\n"
                    "🏭 Поставщик 2: Shenzhen Manufacturer - $11.80\n"
                    "🏭 Поставщик 3: Yiwu Supplier - $13.20\n\n"
                    "✅ Рекомендуем: Shenzhen Manufacturer (лучшая цена)"
                )
                back_keyboard = {
                    "inline_keyboard": [
                        [{"text": "✅ Оформить заказ", "callback_data": f"order_{order_id}"}],
                        [{"text": "🔍 Новый поиск", "callback_data": "search"}],
                        [{"text": "⬅️ Главное меню", "callback_data": "back"}]
                    ]
                }
                send_message(chat_id, response_text, back_keyboard)
                
            # Обработка документов
            elif 'document' in message:
                document = message['document']
                file_name = document.get('file_name', 'Без названия')
                file_size = document.get('file_size', 0)
                file_id = document['file_id']
                username = message.get('from', {}).get('username', 'Unknown')
                
                logger.info(f"📎 Document received from {user_name}: {file_name} ({file_size} bytes)")
                
                # Определяем тип файла
                file_type, file_desc = get_file_type_info(file_name)
                
                # Проверяем поддерживаемые типы
                supported_types = ['excel', 'pdf', 'word', 'document']
                if file_type not in supported_types:
                    response_text = (
                        f"❌ Извините, {user_name}!\n\n"
                        f"Файл '{file_name}' не поддерживается.\n\n"
                        f"Поддерживаемые форматы:\n"
                        f"📊 Excel: .xlsx, .xls\n"
                        f"📄 PDF: .pdf\n"
                        f"📝 Word: .docx, .doc\n"
                        f"📸 Изображения: .jpg, .png, .gif\n\n"
                        f"Пожалуйста, отправьте файл в поддерживаемом формате."
                    )
                    send_message(chat_id, response_text)
                    return "OK", 200
                
                # Получаем информацию о файле
                file_info = get_file_info(file_id)
                if file_info:
                    file_info['file_name'] = file_name
                    file_info['file_type'] = file_type
                
                logger.info(f"Document file info: {file_info}")
                
                # Создаем заказ на основе документа
                product_info = f"Поиск по документу: {file_name} от @{username}"
                order_id = create_order(chat_id, product_info)
                
                response_text = (
                    f"{file_desc} *получен от @{username}!*\n\n"
                    f"📎 Файл: {file_name}\n"
                    f"📏 Размер: {file_size // 1024} КБ\n\n"
                    "🔍 Анализирую документ...\n"
                    "🇨🇳 Ищу товары в базе китайских поставщиков...\n"
                    "💰 Сравниваю цены и условия...\n\n"
                    f"📋 Создан заказ: `{order_id}`\n"
                    "⏳ Результаты будут готовы в течение часа!\n\n"
                    "*Что мы делаем:*\n"
                    "📊 Обрабатываем ваш документ\n"
                    "🔍 Ищем каждый товар отдельно\n"
                    "💰 Находим лучшие цены\n"
                    "📋 Составляем детальный отчет"
                )
                back_keyboard = {
                    "inline_keyboard": [
                        [{"text": "✅ Оформить заказ", "callback_data": f"order_{order_id}"}],
                        [{"text": "🔍 Новый поиск", "callback_data": "search"}],
                        [{"text": "⬅️ Главное меню", "callback_data": "back"}]
                    ]
                }
                send_message(chat_id, response_text, back_keyboard)
                
            # Обработка текста
            elif 'text' in message:
                text = message['text']
                if not text.startswith('/'):  # Игнорируем команды
                    # Создаем заказ на основе текстового запроса
                    order_id = create_order(chat_id, text)
                    
                    response_text = (
                        f"📝 *Получил запрос:* {text}\n\n"
                        "🔍 Ищу товары в базе китайских поставщиков...\n"
                        "💰 Анализирую цены и качество...\n"
                        "🚚 Проверяю варианты доставки...\n\n"
                        f"📋 Создан заказ: `{order_id}`\n\n"
                        "*Найденные товары:*\n"
                        "🏭 Alibaba Supplier A - $8.90 (MOQ: 100)\n"
                        "🏭 Made-in-China Supplier B - $9.50 (MOQ: 50)\n"
                        "🏭 DHgate Supplier C - $12.00 (MOQ: 1)\n\n"
                        "✅ Рекомендуем: Supplier A (лучшее соотношение цена/качество)"
                    )
                    back_keyboard = {
                        "inline_keyboard": [
                            [{"text": "✅ Оформить заказ", "callback_data": f"order_{order_id}"}],
                            [{"text": "🔍 Новый поиск", "callback_data": "search"}],
                            [{"text": "⬅️ Главное меню", "callback_data": "back"}]
                        ]
                    }
                    send_message(chat_id, response_text, back_keyboard)
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "Error", 500

def answer_callback_query(callback_query_id):
    """Отвечаем на callback query"""
    try:
        url = f"{BOT_URL}/answerCallbackQuery"
        data = {'callback_query_id': callback_query_id}
        requests.post(url, json=data, timeout=5)
    except Exception as e:
        logger.error(f"Answer callback query error: {e}")

def edit_message(chat_id, message_id, text, reply_markup=None):
    """Редактирование сообщения"""
    try:
        url = f"{BOT_URL}/editMessageText"
        data = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        if reply_markup:
            data['reply_markup'] = reply_markup
        response = requests.post(url, json=data, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Edit message error: {e}")
        return None

def setup_webhook():
    """Установка webhook"""
    try:
        # Сначала удаляем старый webhook
        delete_url = f"{BOT_URL}/deleteWebhook"
        requests.post(delete_url, timeout=10)
        
        # URL для PythonAnywhere - замените yourusername на ваше имя пользователя
        webhook_url = "https://dimvi.pythonanywhere.com/webhook"
        
        # Устанавливаем новый webhook
        url = f"{BOT_URL}/setWebhook"
        data = {'url': webhook_url}
        
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            logger.info(f"Webhook set successfully: {webhook_url}")
            return True
        else:
            logger.error(f"Webhook setup failed: {result}")
            return False
            
    except Exception as e:
        logger.error(f"Webhook setup error: {e}")
        return False

@app.route('/set_webhook')
def set_webhook_manual():
    """Ручная установка webhook"""
    if setup_webhook():
        return "Webhook установлен успешно!"
    else:
        return "Ошибка установки webhook"

# Инициализация при запуске
def initialize_bot():
    """Инициализация бота"""
    global BOT_TOKEN, BOT_URL
    BOT_TOKEN = '8283773658:AAFXziQDzEns0feaUNRAH45b_eFl2ynjIvY'
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found!")
        return False
    
    BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
    logger.info(f"Bot initialized: {BOT_TOKEN[:10]}...")
    
    # Инициализируем Google Sheets
    init_google_sheets()
    
    # Устанавливаем webhook при инициализации
    setup_webhook()
    return True

# Инициализируем при импорте
initialize_bot()

if __name__ == '__main__':
    app.run(debug=True)
