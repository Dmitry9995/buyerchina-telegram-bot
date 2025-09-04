from typing import Dict, List, Set, Optional
from datetime import datetime
from .order_management import Order, OrderStatus, OrderManagementService
from .logistics_tracking import LogisticsTrackingService

class AdminService:
    def __init__(self, order_service: OrderManagementService, logistics_service: LogisticsTrackingService, google_sheets_service=None):
        # Список ID администраторов (в реальном проекте это должно быть в базе данных)
        self.admin_users: Set[int] = {
            123456789,  # Замените на реальные Telegram ID администраторов
            987654321,  # Добавьте ID менеджеров BuyerChina
            1169659218  # Ваш Telegram ID для тестирования
        }
        
        self.order_service = order_service
        self.logistics_service = logistics_service
        self.google_sheets_service = google_sheets_service
    
    def is_admin(self, user_id: int) -> bool:
        """Проверить, является ли пользователь администратором"""
        return user_id in self.admin_users
    
    def get_google_sheets_url(self) -> Optional[str]:
        """Получить ссылку на Google Sheets таблицу"""
        if self.google_sheets_service and self.google_sheets_service.is_connected():
            return self.google_sheets_service.get_spreadsheet_url()
        return None
    
    def get_sheets_status(self, language_service=None, user_id=None) -> str:
        """Получить статус подключения к Google Sheets"""
        if self.google_sheets_service and self.google_sheets_service.is_connected():
            if language_service and user_id:
                return language_service.get_text(user_id, 'sheets_connected')
            return "✅ Подключено"
        else:
            if language_service and user_id:
                return language_service.get_text(user_id, 'sheets_disconnected')
            return "❌ Не подключено"
    
    def add_admin(self, user_id: int) -> bool:
        """Добавить администратора"""
        self.admin_users.add(user_id)
        return True
    
    def remove_admin(self, user_id: int) -> bool:
        """Удалить администратора"""
        if user_id in self.admin_users:
            self.admin_users.remove(user_id)
            return True
        return False
    
    def get_all_orders(self) -> List[Order]:
        """Получить все заказы для администраторов"""
        all_orders = []
        for orders in self.order_service.user_orders.values():
            for order_id in orders:
                order = self.order_service.get_order(order_id)
                if order:
                    all_orders.append(order)
        return sorted(all_orders, key=lambda x: x.created_date, reverse=True)
    
    def get_orders_by_status(self, status: OrderStatus) -> List[Order]:
        """Получить заказы по статусу"""
        all_orders = self.get_all_orders()
        return [order for order in all_orders if order.status == status]
    
    def format_admin_dashboard(self, language_service=None, user_id=None) -> str:
        """Форматировать панель администратора"""
        all_orders = self.get_all_orders()
        
        # Статистика по статусам
        status_counts = {}
        for status in OrderStatus:
            status_counts[status] = len([o for o in all_orders if o.status == status])
        
        total_amount = sum(order.total_amount for order in all_orders)
        
        if language_service and user_id:
            lang = language_service.get_user_language(user_id)
            if lang == 'ru':
                message = "👨‍💼 **Панель администратора BuyerChina**\n\n"
                message += f"📊 **Статистика заказов:**\n"
                message += f"• Всего заказов: {len(all_orders)}\n"
                message += f"• Ожидают: {status_counts[OrderStatus.PENDING]}\n"
                message += f"• Подтверждены: {status_counts[OrderStatus.CONFIRMED]}\n"
                message += f"• В производстве: {status_counts[OrderStatus.PRODUCTION]}\n"
                message += f"• Отправлены: {status_counts[OrderStatus.SHIPPED]}\n"
                message += f"• Доставлены: {status_counts[OrderStatus.DELIVERED]}\n"
                message += f"• Отменены: {status_counts[OrderStatus.CANCELLED]}\n\n"
                message += f"💰 **Общая сумма:** ${total_amount:,.2f}\n\n"
                message += "Выберите действие:"
            else:
                message = "👨‍💼 **BuyerChina Admin Dashboard**\n\n"
                message += f"📊 **Order Statistics:**\n"
                message += f"• Total Orders: {len(all_orders)}\n"
                message += f"• Pending: {status_counts[OrderStatus.PENDING]}\n"
                message += f"• Confirmed: {status_counts[OrderStatus.CONFIRMED]}\n"
                message += f"• In Production: {status_counts[OrderStatus.PRODUCTION]}\n"
                message += f"• Shipped: {status_counts[OrderStatus.SHIPPED]}\n"
                message += f"• Delivered: {status_counts[OrderStatus.DELIVERED]}\n"
                message += f"• Cancelled: {status_counts[OrderStatus.CANCELLED]}\n\n"
                message += f"💰 **Total Amount:** ${total_amount:,.2f}\n\n"
                message += "Select an action:"
        else:
            message = "👨‍💼 **BuyerChina Admin Dashboard**\n\n"
            message += f"📊 **Order Statistics:**\n"
            message += f"• Total Orders: {len(all_orders)}\n"
            message += f"• Pending: {status_counts[OrderStatus.PENDING]}\n"
            message += f"• Confirmed: {status_counts[OrderStatus.CONFIRMED]}\n"
            message += f"• In Production: {status_counts[OrderStatus.PRODUCTION]}\n"
            message += f"• Shipped: {status_counts[OrderStatus.SHIPPED]}\n"
            message += f"• Delivered: {status_counts[OrderStatus.DELIVERED]}\n"
            message += f"• Cancelled: {status_counts[OrderStatus.CANCELLED]}\n\n"
            message += f"💰 **Total Amount:** ${total_amount:,.2f}\n\n"
            message += "Select an action:"
        
        return message
    
    def format_orders_list(self, orders: List[Order], language_service=None, user_id=None) -> str:
        """Форматировать список заказов для администратора"""
        if not orders:
            if language_service and user_id:
                lang = language_service.get_user_language(user_id)
                if lang == 'ru':
                    return "📦 Заказы не найдены."
            return "📦 No orders found."
        
        if language_service and user_id:
            lang = language_service.get_user_language(user_id)
            if lang == 'ru':
                message = f"📋 **Список заказов ({len(orders)} шт.)**\n\n"
            else:
                message = f"📋 **Orders List ({len(orders)} total)**\n\n"
        else:
            message = f"📋 **Orders List ({len(orders)} total)**\n\n"
        
        for order in orders[:10]:  # Показать первые 10 заказов
            status_emoji = self.order_service._get_status_emoji(order.status)
            message += f"**{order.order_id}** {status_emoji}\n"
            message += f"👤 User ID: {order.user_id}\n"
            message += f"🏭 {order.supplier}\n"
            message += f"💰 ${order.total_amount:,.2f}\n"
            message += f"📅 {order.created_date.strftime('%Y-%m-%d %H:%M')}\n"
            
            if order.tracking_number:
                message += f"📦 {order.tracking_number}\n"
            
            message += "\n"
        
        if len(orders) > 10:
            if language_service and user_id:
                lang = language_service.get_user_language(user_id)
                if lang == 'ru':
                    message += f"... и еще {len(orders) - 10} заказов"
                else:
                    message += f"... and {len(orders) - 10} more orders"
            else:
                message += f"... and {len(orders) - 10} more orders"
        
        return message
    
    def update_order_status(self, order_id: str, new_status: OrderStatus, tracking_number: str = None) -> bool:
        """Обновить статус заказа"""
        return self.order_service.update_order_status(order_id, new_status, tracking_number)
    
    def get_order_details(self, order_id: str) -> Optional[Order]:
        """Получить детали заказа"""
        return self.order_service.get_order(order_id)
