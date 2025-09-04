#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BuyerChina Telegram Bot - Production Version
Улучшенная версия бота для непрерывной работы в продакшене
"""

import os
import logging
import sys
import signal
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from telegram.error import NetworkError, TimedOut, BadRequest

# Import our services
from services.product_request_service import ProductRequestService
from services.supplier_verification import SupplierVerificationService
from services.order_management import OrderManagementService, OrderStatus
from services.logistics_tracking import LogisticsTrackingService
from services.language_service import LanguageService
from services.admin_service import AdminService
from services.google_sheets_service import GoogleSheetsService

# Load environment variables
load_dotenv()

# Enhanced logging configuration for production
def setup_logging():
    """Настройка расширенного логирования для продакшена"""
    # Создаем директорию для логов если её нет
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Настройка форматирования
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # Основной логгер
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Консольный вывод с правильной кодировкой
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    if hasattr(console_handler.stream, 'reconfigure'):
        console_handler.stream.reconfigure(encoding='utf-8')
    logger.addHandler(console_handler)
    
    # Файл для всех логов
    file_handler = logging.FileHandler(
        os.path.join(log_dir, f'bot_{datetime.now().strftime("%Y%m%d")}.log'),
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Файл только для ошибок
    error_handler = logging.FileHandler(
        os.path.join(log_dir, f'bot_errors_{datetime.now().strftime("%Y%m%d")}.log'),
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    return logger

logger = setup_logging()

# Bot token from environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Conversation states
SEARCH_PRODUCT, VERIFY_SUPPLIER, TRACK_SHIPMENT, SELECT_LANGUAGE, ADMIN_PANEL = range(5)

# Additional states for new functionality
AWAIT_PRODUCT_DESCRIPTION, AWAIT_PRODUCT_IMAGE = range(5, 7)

# Global services - will be initialized in main()
product_request_service = None
supplier_service = None
order_service = None
logistics_service = None
language_service = None
google_sheets_service = None
admin_service = None

# Graceful shutdown handling
shutdown_event = asyncio.Event()

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    logger.info(f"Получен сигнал {signum}. Начинаю graceful shutdown...")
    shutdown_event.set()

# Error handling decorator
def handle_errors(func):
    """Декоратор для обработки ошибок в хендлерах"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            return await func(update, context)
        except Exception as e:
            logger.error(f"Ошибка в {func.__name__}: {e}", exc_info=True)
            
            # Попытка отправить сообщение об ошибке пользователю
            try:
                user_id = update.effective_user.id if update.effective_user else None
                error_message = "Произошла ошибка. Попробуйте позже или обратитесь к администратору."
                
                if language_service and user_id:
                    error_message = language_service.get_text(user_id, 'error_occurred', 
                                                            default=error_message)
                
                if update.callback_query:
                    await update.callback_query.answer(error_message, show_alert=True)
                elif update.message:
                    await update.message.reply_text(error_message)
                    
            except Exception as send_error:
                logger.error(f"Не удалось отправить сообщение об ошибке: {send_error}")
            
            return ConversationHandler.END
    
    return wrapper

# Command Handlers with error handling
@handle_errors
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    logger.info(f"Пользователь {update.effective_user.id} запустил бота")
    await start_menu(update, context)

@handle_errors
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses from the inline keyboard."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    logger.info(f"Пользователь {user_id} нажал кнопку: {query.data}")
    
    if query.data == 'search':
        await show_search_options(update, context)
        return SEARCH_PRODUCT
    elif query.data == 'search_text':
        message = language_service.get_text(user_id, 'product_search_title')
        await query.edit_message_text(message, parse_mode='Markdown')
        return SEARCH_PRODUCT
    elif query.data == 'search_image':
        message = language_service.get_text(user_id, 'product_image_title', 
                                          default="📸 **Поиск товара по изображению**\n\nОтправьте фотографию товара, который вы ищете.")
        await query.edit_message_text(message, parse_mode='Markdown')
        return AWAIT_PRODUCT_IMAGE
    elif query.data == 'verify':
        message = language_service.get_text(user_id, 'supplier_verification_title')
        await query.edit_message_text(message, parse_mode='Markdown')
        return VERIFY_SUPPLIER
    elif query.data == 'orders':
        orders = order_service.get_user_orders(user_id)
        message = order_service.format_order_summary(orders, language_service, user_id)
        
        back_text = language_service.get_text(user_id, 'back_menu')
        keyboard = [[InlineKeyboardButton(back_text, callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    elif query.data == 'tracking':
        message = language_service.get_text(user_id, 'track_shipment_title')
        await query.edit_message_text(message, parse_mode='Markdown')
        return TRACK_SHIPMENT
    elif query.data == 'language':
        await show_language_selection(update, context)
        return SELECT_LANGUAGE
    elif query.data == 'admin':
        if admin_service.is_admin(user_id):
            await show_admin_panel(update, context)
            return ADMIN_PANEL
        else:
            access_denied = language_service.get_text(user_id, 'access_denied')
            await query.edit_message_text(access_denied)
            return ConversationHandler.END
    elif query.data.startswith('admin_'):
        if not admin_service.is_admin(user_id):
            access_denied = language_service.get_text(user_id, 'access_denied')
            await query.edit_message_text(access_denied)
            return ConversationHandler.END
        
        action = query.data.split('_')[1]
        if action == 'all':
            orders = admin_service.get_all_orders()
            message = admin_service.format_orders_list(orders, language_service, user_id)
        elif action == 'pending':
            orders = admin_service.get_orders_by_status(OrderStatus.PENDING)
            message = admin_service.format_orders_list(orders, language_service, user_id)
        elif action == 'active':
            active_orders = []
            for status in [OrderStatus.CONFIRMED, OrderStatus.PRODUCTION, OrderStatus.SHIPPED]:
                active_orders.extend(admin_service.get_orders_by_status(status))
            message = admin_service.format_orders_list(active_orders, language_service, user_id)
        else:
            message = "Unknown action"
        
        back_text = language_service.get_text(user_id, 'back_menu')
        admin_text = language_service.get_text(user_id, 'admin_panel')
        keyboard = [
            [InlineKeyboardButton(admin_text, callback_data='admin')],
            [InlineKeyboardButton(back_text, callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    elif query.data.startswith('lang_'):
        lang_code = query.data.split('_')[1]
        language_service.set_user_language(user_id, lang_code)
        
        success_message = language_service.get_text(user_id, 'language_changed')
        await query.edit_message_text(success_message)
        
        # Return to main menu after 1 second
        await asyncio.sleep(1)
        await start_menu(update, context)
        return ConversationHandler.END
    elif query.data == 'help':
        await show_help(update, context)
    elif query.data == 'back':
        await start_menu(update, context)
    
    return ConversationHandler.END

@handle_errors
async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        "*BuyerChina Bot Help*\n\n"
        "*Available Commands:*\n"
        "/start - Start the bot and show main menu\n"
        "/help - Show this help message\n"
        "/search - Search for products\n"
        "/verify - Verify a supplier\n"
        "/track - Track your shipment\n\n"
        "*How to Use:*\n"
        "1. Use the menu buttons to navigate\n"
        "2. Follow the prompts for each action\n"
        "3. Contact support if you need assistance"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data='back')]
            ])
        )
    else:
        await update.message.reply_text(help_text, parse_mode='Markdown')

@handle_errors
async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product search queries - send to manager via Google Sheets."""
    user_id = update.effective_user.id
    description = update.message.text
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)
    
    logger.info(f"Пользователь {user_id} отправил запрос на поиск: {description}")
    
    # Создаем запрос через новый сервис
    request = product_request_service.create_product_request(
        user_id=user_id,
        username=username,
        description=description
    )
    
    # Форматируем подтверждение
    message = product_request_service.format_request_confirmation(request, language_service, user_id)
    
    new_search_text = language_service.get_text(user_id, 'new_search')
    back_text = language_service.get_text(user_id, 'back_menu')
    
    keyboard = [
        [InlineKeyboardButton(new_search_text, callback_data='search')],
        [InlineKeyboardButton(back_text, callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    return ConversationHandler.END

@handle_errors
async def show_search_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show search type selection menu."""
    user_id = update.callback_query.from_user.id if update.callback_query else update.effective_user.id
    
    if language_service.get_user_language(user_id) == 'ru':
        message = "🔍 **Поиск товаров**\n\nВыберите способ поиска:"
        text_button = "📝 Поиск по описанию"
        image_button = "📸 Поиск по изображению"
    else:
        message = "🔍 **Product Search**\n\nChoose search method:"
        text_button = "📝 Search by description"
        image_button = "📸 Search by image"
    
    back_text = language_service.get_text(user_id, 'back_menu')
    
    keyboard = [
        [InlineKeyboardButton(text_button, callback_data='search_text')],
        [InlineKeyboardButton(image_button, callback_data='search_image')],
        [InlineKeyboardButton(back_text, callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message, parse_mode='Markdown', reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            message, parse_mode='Markdown', reply_markup=reply_markup
        )

@handle_errors
async def handle_image_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle product search by image."""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)
    
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        description = f"Поиск товара по изображению (ID: {photo.file_id})"
        if update.message.caption:
            description += f"\nОписание: {update.message.caption}"
        
        logger.info(f"Пользователь {user_id} отправил изображение для поиска")
        
        request = product_request_service.create_product_request(
            user_id=user_id,
            username=username,
            description=description,
            image_url=file.file_path
        )
        
        message = product_request_service.format_request_confirmation(request, language_service, user_id)
    else:
        message = language_service.get_text(user_id, 'no_image_provided', 
                                          default="❌ Изображение не найдено. Пожалуйста, отправьте фотографию товара.")
    
    new_search_text = language_service.get_text(user_id, 'new_search')
    back_text = language_service.get_text(user_id, 'back_menu')
    
    keyboard = [
        [InlineKeyboardButton(new_search_text, callback_data='search')],
        [InlineKeyboardButton(back_text, callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    return ConversationHandler.END

@handle_errors
async def handle_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle supplier verification requests."""
    user_id = update.effective_user.id
    company_name = update.message.text
    logger.info(f"Пользователь {user_id} проверяет поставщика: {company_name}")
    
    supplier = supplier_service.verify_supplier(company_name)
    
    if supplier:
        message = supplier_service.format_verification_report(supplier, language_service, user_id)
        risk_assessment = supplier_service.get_risk_assessment(supplier, language_service, user_id)
        full_message = f"{message}\n\n{risk_assessment}"
    else:
        full_message = language_service.get_text(user_id, 'supplier_not_found', name=company_name)
    
    verify_another_text = language_service.get_text(user_id, 'verify_another')
    back_text = language_service.get_text(user_id, 'back_menu')
    
    keyboard = [
        [InlineKeyboardButton(verify_another_text, callback_data='verify')],
        [InlineKeyboardButton(back_text, callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(full_message, parse_mode='Markdown', reply_markup=reply_markup)
    return ConversationHandler.END

@handle_errors
async def handle_tracking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle shipment tracking requests."""
    user_id = update.effective_user.id
    tracking_number = update.message.text.strip().upper()
    logger.info(f"Пользователь {user_id} отслеживает: {tracking_number}")
    
    shipment = logistics_service.track_shipment(tracking_number)
    
    if shipment:
        message = logistics_service.format_tracking_info(shipment, language_service, user_id)
        delivery_estimate = logistics_service.get_delivery_estimate(tracking_number)
        if delivery_estimate:
            message += f"\n\n{delivery_estimate}"
    else:
        message = language_service.get_text(user_id, 'tracking_not_found', number=tracking_number)
    
    track_another_text = language_service.get_text(user_id, 'track_another')
    back_text = language_service.get_text(user_id, 'back_menu')
    
    keyboard = [
        [InlineKeyboardButton(track_another_text, callback_data='tracking')],
        [InlineKeyboardButton(back_text, callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    return ConversationHandler.END

@handle_errors
async def show_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show language selection menu."""
    user_id = update.callback_query.from_user.id if update.callback_query else update.effective_user.id
    
    message = language_service.get_text(user_id, 'select_language')
    languages = language_service.get_available_languages()
    
    keyboard = []
    for code, name in languages.items():
        keyboard.append([InlineKeyboardButton(name, callback_data=f'lang_{code}')])
    
    back_text = language_service.get_text(user_id, 'back_menu')
    keyboard.append([InlineKeyboardButton(back_text, callback_data='back')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message, parse_mode='Markdown', reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            message, parse_mode='Markdown', reply_markup=reply_markup
        )

@handle_errors
async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel."""
    user_id = update.callback_query.from_user.id if update.callback_query else update.effective_user.id
    
    if not admin_service.is_admin(user_id):
        access_denied = language_service.get_text(user_id, 'access_denied')
        if update.callback_query:
            await update.callback_query.edit_message_text(access_denied)
        else:
            await update.message.reply_text(access_denied)
        return
    
    message = admin_service.format_admin_dashboard(language_service, user_id)
    
    # Добавляем информацию о Google Sheets
    sheets_status = admin_service.get_sheets_status(language_service, user_id)
    message += f"\n📊 Google Sheets: {sheets_status}"
    
    # Get localized button texts
    all_orders_text = language_service.get_text(user_id, 'view_all_orders')
    pending_text = language_service.get_text(user_id, 'view_pending')
    active_text = language_service.get_text(user_id, 'view_active')
    back_text = language_service.get_text(user_id, 'back_menu')
    
    keyboard = [
        [InlineKeyboardButton(all_orders_text, callback_data='admin_all')],
        [InlineKeyboardButton(pending_text, callback_data='admin_pending')],
        [InlineKeyboardButton(active_text, callback_data='admin_active')]
    ]
    
    # Добавляем кнопку Google Sheets если подключено
    sheets_url = admin_service.get_google_sheets_url()
    if sheets_url:
        sheets_button_text = language_service.get_text(user_id, 'google_sheets_button')
        keyboard.append([InlineKeyboardButton(sheets_button_text, url=sheets_url)])
    
    keyboard.append([InlineKeyboardButton(back_text, callback_data='back')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message, parse_mode='Markdown', reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            message, parse_mode='Markdown', reply_markup=reply_markup
        )

@handle_errors
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation."""
    user_id = update.effective_user.id
    message = language_service.get_text(user_id, 'cancel')
    await update.message.reply_text(message)
    return ConversationHandler.END

@handle_errors
async def start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the main menu."""
    if update.callback_query:
        user = update.callback_query.from_user
        query = update.callback_query
    else:
        user = update.effective_user
        query = None
    
    user_id = user.id
    welcome_message = language_service.get_text(user_id, 'welcome', name=user.first_name)
    
    # Синхронизация активности пользователя с Google Sheets
    if google_sheets_service.is_connected():
        try:
            user_info = {
                'username': user.username or '',
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'language': language_service.get_user_language(user_id),
                'first_interaction': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'orders_count': len(order_service.get_user_orders(user_id)),
                'total_spent': sum(order.total_amount for order in order_service.get_user_orders(user_id)),
                'status': 'active'
            }
            google_sheets_service.sync_user_activity(user_id, user_info)
        except Exception as e:
            logger.error(f"Ошибка синхронизации с Google Sheets: {e}")
    
    # Get localized button texts
    search_text = language_service.get_text(user_id, 'search_products')
    verify_text = language_service.get_text(user_id, 'verify_supplier')
    orders_text = language_service.get_text(user_id, 'my_orders')
    tracking_text = language_service.get_text(user_id, 'track_shipment')
    help_text = language_service.get_text(user_id, 'help')
    language_text = language_service.get_text(user_id, 'language')
    
    keyboard = [
        [InlineKeyboardButton(search_text, callback_data='search')],
        [InlineKeyboardButton(verify_text, callback_data='verify')],
        [InlineKeyboardButton(orders_text, callback_data='orders')],
        [InlineKeyboardButton(tracking_text, callback_data='tracking')],
        [InlineKeyboardButton(help_text, callback_data='help'),
         InlineKeyboardButton(language_text, callback_data='language')],
    ]
    
    # Add admin button for administrators
    if admin_service.is_admin(user_id):
        admin_text = language_service.get_text(user_id, 'admin_panel')
        keyboard.append([InlineKeyboardButton(admin_text, callback_data='admin')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(
            welcome_message, reply_markup=reply_markup, parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            welcome_message, reply_markup=reply_markup, parse_mode='Markdown'
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    
    # Отправляем уведомление администратору о критических ошибках
    if isinstance(context.error, (NetworkError, TimedOut)):
        logger.warning("Сетевая ошибка, переподключение...")
    else:
        # Для других ошибок отправляем уведомление админу
        admin_ids = admin_service.get_admin_ids() if admin_service else []
        for admin_id in admin_ids:
            try:
                error_message = f"🚨 Ошибка в боте:\n{str(context.error)[:500]}"
                await context.bot.send_message(chat_id=admin_id, text=error_message)
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление админу {admin_id}: {e}")

def initialize_services():
    """Инициализация всех сервисов"""
    global product_request_service, supplier_service, order_service, logistics_service
    global language_service, google_sheets_service, admin_service
    
    logger.info("Инициализация сервисов...")
    
    try:
        supplier_service = SupplierVerificationService()
        order_service = OrderManagementService()
        logistics_service = LogisticsTrackingService()
        language_service = LanguageService()
        google_sheets_service = GoogleSheetsService()
        product_request_service = ProductRequestService(google_sheets_service)
        admin_service = AdminService(order_service, logistics_service, google_sheets_service)
        
        logger.info("✅ Все сервисы инициализированы успешно")
        
        # Проверяем подключение к Google Sheets
        if google_sheets_service.is_connected():
            logger.info("✅ Google Sheets подключены успешно")
        else:
            logger.warning("⚠️ Google Sheets не подключены")
            
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации сервисов: {e}")
        raise

async def health_check():
    """Периодическая проверка здоровья бота"""
    while not shutdown_event.is_set():
        try:
            # Проверяем состояние сервисов
            logger.info("🔍 Проверка состояния сервисов...")
            
            # Проверяем Google Sheets
            if google_sheets_service and google_sheets_service.is_connected():
                logger.info("✅ Google Sheets работают")
            else:
                logger.warning("⚠️ Проблемы с Google Sheets")
            
            # Ждем 5 минут до следующей проверки
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"Ошибка в health_check: {e}")
            await asyncio.sleep(60)  # Короткая пауза при ошибке

async def main():
    """Start the bot with enhanced error handling and monitoring."""
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        return
    
    # Настройка обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Инициализация сервисов
    initialize_services()
    
    # Create the Application with enhanced settings
    application = Application.builder().token(TOKEN).build()
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button, pattern='^(search|verify|tracking|language|admin)$'),
        ],
        states={
            SEARCH_PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search)],
            VERIFY_SUPPLIER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_verification)],
            TRACK_SHIPMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tracking)],
            AWAIT_PRODUCT_IMAGE: [MessageHandler(filters.PHOTO, handle_image_search)],
            SELECT_LANGUAGE: [CallbackQueryHandler(button, pattern='^lang_')],
            ADMIN_PANEL: [CallbackQueryHandler(button, pattern='^admin_')],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", show_help))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button))

    logger.info("🚀 Запуск BuyerChina Bot (Production Version)...")
    
    try:
        # Запускаем health check в фоне
        health_task = asyncio.create_task(health_check())
        
        # Start the Bot with polling
        await application.initialize()
        await application.start()
        await application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            timeout=30,
            read_timeout=10,
            write_timeout=10,
            connect_timeout=10,
            pool_timeout=10
        )
        
        logger.info("✅ Бот успешно запущен и работает")
        
        # Ждем сигнала завершения
        await shutdown_event.wait()
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
    finally:
        logger.info("🛑 Завершение работы бота...")
        
        # Отменяем health check
        if 'health_task' in locals():
            health_task.cancel()
        
        # Graceful shutdown
        if application.updater.running:
            await application.updater.stop()
        await application.stop()
        await application.shutdown()
        
        logger.info("✅ Бот завершил работу")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания")
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}", exc_info=True)
        sys.exit(1)
