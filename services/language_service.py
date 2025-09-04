from typing import Dict, Optional
import json

class LanguageService:
    def __init__(self):
        self.user_languages: Dict[int, str] = {}  # user_id -> language_code
        self.default_language = "en"
        
        # Language translations
        self.translations = {
            "en": {
                # Main menu
                "welcome": "👋 Welcome to BuyerChina, {name}!\n\nI'm here to assist you with:\n• 🔍 Product search and sourcing\n• 🏢 Supplier verification\n• 🛒 Purchase assistance\n• 🚚 Logistics support\n\nUse the menu below to get started!",
                "search_products": "🔍 Search Products",
                "verify_supplier": "🏢 Verify Supplier", 
                "my_orders": "🛒 My Orders",
                "track_shipment": "📦 Track Shipment",
                "help": "ℹ️ Help",
                "language": "🌐 Language",
                "back_menu": "⬅️ Back to Menu",
                
                # Product search
                "product_search_title": "🔍 *Product Search*\n\nPlease enter the name or description of the product you're looking for.",
                "products_found": "🔍 **Found {count} products:**",
                "no_products": "❌ No products found. Try a different search term.",
                "new_search": "🔍 New Search",
                'contact_quote': '💡 *Contact us to get detailed quotes and supplier verification!*\n\n🚚 *Logistics and shipping costs are calculated separately based on your location and order volume.*',
                
                # Supplier verification
                "supplier_verification_title": "🏢 *Supplier Verification*\n\nPlease provide the company name or website you'd like to verify.",
                "verification_report": "🏢 **Supplier Verification Report**",
                "supplier_not_found": "❌ *Supplier Not Found*\n\nWe couldn't find verification data for '{name}'.\n\n💡 *What we can do:*\n• Manual verification research\n• On-site inspection services\n• Business license verification\n• Factory audit reports\n\nContact our team for custom verification services!",
                "verify_another": "🏢 Verify Another",
                "risk_assessment": "🔍 **Risk Assessment for {name}**",
                "recommended_supplier": "✅ **Recommended Supplier**",
                "proceed_caution": "⚠️ **Proceed with Caution**",
                "high_risk": "❌ **High Risk - Not Recommended**",
                
                # Orders
                "no_orders": "📦 No orders found.\n\n💡 Start by searching for products and contact us to place your first order!",
                "your_orders": "📦 **Your Orders ({count} total)**",
                "order_details": "📋 **Order Details**",
                
                # Tracking
                "track_shipment_title": "📦 *Track Shipment*\n\nPlease enter your tracking number:",
                "shipment_tracking": "📦 **Shipment Tracking**",
                "tracking_not_found": "❌ *Tracking Number Not Found*\n\nWe couldn't find information for tracking number: `{number}`\n\n💡 *Please check:*\n• Tracking number is correct\n• Package has been shipped\n• Try again in a few hours\n\nContact us if you need assistance!",
                "track_another": "📦 Track Another",
                "tracking_history": "📍 Tracking History:",
                
                # Language selection
                "select_language": "🌐 **Select Language**\n\nChoose your preferred language:",
                "language_changed": "✅ Language changed to English",
                
                # Help
                "help_title": "*BuyerChina Bot Help*",
                "available_commands": "*Available Commands:*",
                "how_to_use": "*How to Use:*",
                
                # Admin panel
                "admin_panel": "👨‍💼 Admin Panel",
                "admin_dashboard": "👨‍💼 **BuyerChina Admin Dashboard**",
                "order_statistics": "📊 **Order Statistics:**",
                "total_orders": "Total Orders:",
                "pending_orders": "Pending:",
                "confirmed_orders": "Confirmed:",
                "production_orders": "In Production:",
                "shipped_orders": "Shipped:",
                "delivered_orders": "Delivered:",
                "cancelled_orders": "Cancelled:",
                "total_amount": "💰 **Total Amount:**",
                "select_action": "Select an action:",
                "view_all_orders": "View All Orders",
                "view_pending": "Pending Orders",
                "view_active": "Active Orders",
                "order_management": "⚙️ Order Management",
                "access_denied": "❌ Access denied. Admin privileges required.",
                "orders_list": "📋 **Orders List ({count} total)**",
                "no_orders_found": "📦 No orders found.",
                "user_id": "User ID:",
                "google_sheets_button": "📊 Open Google Sheets",
                "sheets_connected": "✅ Connected",
                "sheets_disconnected": "❌ Not connected",
                
                # General
                "cancel": "Operation cancelled. Use /start to return to the main menu.",
                "company": "Company:",
                "status": "Status:",
                "location": "Location:",
                "price": "Price:",
                "supplier": "Supplier:",
                "min_order": "Min Order:",
                "platform": "Platform:",
                "created": "Created:",
                "total": "Total:",
                "tracking": "Tracking:",
                "carrier": "Carrier:",
                "origin": "Origin:",
                "destination": "Destination:",
                "weight": "Weight:",
                "dimensions": "Dimensions:",
                "est_delivery": "Est. Delivery:",
            },
            "ru": {
                # Main menu
                "welcome": "👋 Добро пожаловать в BuyerChina, {name}!\n\nЯ помогу вам с:\n• 🔍 Поиском и закупкой товаров\n• 🏢 Проверкой поставщиков\n• 🛒 Помощью в покупках\n• 🚚 Логистической поддержкой\n\nИспользуйте меню ниже для начала работы!",
                "search_products": "🔍 Поиск товаров",
                "verify_supplier": "🏢 Проверка поставщика",
                "my_orders": "🛒 Мои заказы", 
                "track_shipment": "📦 Отслеживание",
                "help": "ℹ️ Помощь",
                "language": "🌐 Язык",
                "back_menu": "⬅️ Главное меню",
                
                # Product search
                "product_search_title": "🔍 *Поиск товаров*\n\nВведите название или описание товара, который вы ищете.",
                "products_found": "🔍 **Найдено товаров: {count}**",
                "no_products": "❌ Товары не найдены. Попробуйте другой поисковый запрос.",
                "new_search": "🔍 Новый поиск",
                'contact_quote': '💡 *Свяжитесь с нами для получения подробных котировок и проверки поставщиков!*\n\n🚚 *Логистика и стоимость доставки рассчитываются отдельно в зависимости от вашего местоположения и объема заказа.*',
                
                # Supplier verification
                "supplier_verification_title": "🏢 *Проверка поставщика*\n\nУкажите название компании или веб-сайт для проверки.",
                "verification_report": "🏢 **Отчет о проверке поставщика**",
                "supplier_not_found": "❌ *Поставщик не найден*\n\nМы не смогли найти данные для проверки '{name}'.\n\n💡 *Что мы можем сделать:*\n• Ручная проверка и исследование\n• Услуги инспекции на месте\n• Проверка бизнес-лицензии\n• Отчеты аудита фабрики\n\nСвяжитесь с нашей командой для индивидуальных услуг проверки!",
                "verify_another": "🏢 Проверить другого",
                "risk_assessment": "🔍 **Оценка рисков для {name}**",
                "recommended_supplier": "✅ **Рекомендуемый поставщик**",
                "proceed_caution": "⚠️ **Действовать с осторожностью**",
                "high_risk": "❌ **Высокий риск - Не рекомендуется**",
                
                # Orders
                "no_orders": "📦 Заказы не найдены.\n\n💡 Начните с поиска товаров и свяжитесь с нами для размещения первого заказа!",
                "your_orders": "📦 **Ваши заказы (всего: {count})**",
                "order_details": "📋 **Детали заказа**",
                
                # Tracking
                "track_shipment_title": "📦 *Отслеживание груза*\n\nВведите номер для отслеживания:",
                "shipment_tracking": "📦 **Отслеживание груза**",
                "tracking_not_found": "❌ *Номер отслеживания не найден*\n\nМы не смогли найти информацию по номеру: `{number}`\n\n💡 *Пожалуйста, проверьте:*\n• Правильность номера отслеживания\n• Отправлен ли груз\n• Попробуйте через несколько часов\n\nСвяжитесь с нами, если нужна помощь!",
                "track_another": "📦 Отследить другой",
                "tracking_history": "📍 История отслеживания:",
                
                # Language selection
                "select_language": "🌐 **Выбор языка**\n\nВыберите предпочитаемый язык:",
                "language_changed": "✅ Язык изменен на русский",
                
                # Help
                "help_title": "*Помощь BuyerChina Bot*",
                "available_commands": "*Доступные команды:*",
                "how_to_use": "*Как использовать:*",
                
                # Admin panel
                "admin_panel": "👨‍💼 Админ панель",
                "admin_dashboard": "👨‍💼 **Панель администратора BuyerChina**",
                "order_statistics": "📊 **Статистика заказов:**",
                "total_orders": "Всего заказов:",
                "pending_orders": "Ожидают:",
                "confirmed_orders": "Подтверждены:",
                "production_orders": "В производстве:",
                "shipped_orders": "Отправлены:",
                "delivered_orders": "Доставлены:",
                "cancelled_orders": "Отменены:",
                "total_amount": "💰 **Общая сумма:**",
                "select_action": "Выберите действие:",
                "view_all_orders": "Просмотр всех заказов",
                "view_pending": "Ожидающие заказы",
                "view_active": "Активные заказы",
                "order_management": "⚙️ Управление заказами",
                "access_denied": "❌ Доступ запрещен. Требуются права администратора.",
                "orders_list": "📋 **Список заказов (всего: {count})**",
                "no_orders_found": "📦 Заказы не найдены.",
                "user_id": "ID пользователя:",
                "google_sheets_button": "📊 Открыть Google Sheets",
                "sheets_connected": "✅ Подключено",
                "sheets_disconnected": "❌ Не подключено",
                
                # General
                "cancel": "Операция отменена. Используйте /start для возврата в главное меню.",
                "company": "Компания:",
                "status": "Статус:",
                "location": "Местоположение:",
                "price": "Цена:",
                "supplier": "Поставщик:",
                "min_order": "Мин. заказ:",
                "platform": "Платформа:",
                "created": "Создан:",
                "total": "Итого:",
                "tracking": "Отслеживание:",
                "carrier": "Перевозчик:",
                "origin": "Отправление:",
                "destination": "Назначение:",
                "weight": "Вес:",
                "dimensions": "Размеры:",
                "est_delivery": "Ожид. доставка:",
            }
        }
    
    def set_user_language(self, user_id: int, language_code: str):
        """Set language for a user"""
        if language_code in self.translations:
            self.user_languages[user_id] = language_code
            return True
        return False
    
    def get_user_language(self, user_id: int) -> str:
        """Get user's language, default to English"""
        return self.user_languages.get(user_id, self.default_language)
    
    def get_text(self, user_id: int, key: str, **kwargs) -> str:
        """Get translated text for user"""
        language = self.get_user_language(user_id)
        text = self.translations[language].get(key, self.translations[self.default_language].get(key, key))
        
        # Format with provided arguments
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                return text
        return text
    
    def get_available_languages(self) -> Dict[str, str]:
        """Get available languages"""
        return {
            "en": "🇺🇸 English",
            "ru": "🇷🇺 Русский"
        }
