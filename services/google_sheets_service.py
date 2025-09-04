import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import os
from .order_management import Order, OrderStatus

class GoogleSheetsService:
    def __init__(self):
        self.gc = None
        self.spreadsheet = None
        self.orders_sheet = None
        self.users_sheet = None
        self.analytics_sheet = None
        
        # Настройки Google Sheets
        self.spreadsheet_name = "BuyerChina Orders Tracking"
        self.credentials_file = "credentials.json"  # Файл с учетными данными
        
        # Инициализация подключения
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Инициализация подключения к Google Sheets"""
        try:
            # Проверяем наличие файла с учетными данными
            if not os.path.exists(self.credentials_file):
                print(f"Warning: File {self.credentials_file} not found. Google Sheets integration disabled.")
                return
            
            # Настройка области доступа
            scope = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Авторизация
            creds = Credentials.from_service_account_file(self.credentials_file, scopes=scope)
            self.gc = gspread.authorize(creds)
            
            # Открытие или создание таблицы
            try:
                self.spreadsheet = self.gc.open(self.spreadsheet_name)
            except gspread.SpreadsheetNotFound:
                self.spreadsheet = self.gc.create(self.spreadsheet_name)
                self._setup_sheets()
            
            # Получение листов
            self._get_or_create_sheets()
            
            print("Google Sheets connected successfully!")
            print(f"Spreadsheet URL: {self.get_spreadsheet_url()}")
            
        except Exception as e:
            print(f"Error connecting to Google Sheets: {e}")
            self.gc = None
    
    def _setup_sheets(self):
        """Настройка структуры листов"""
        if not self.spreadsheet:
            return
        
        # Переименование первого листа
        try:
            sheet1 = self.spreadsheet.sheet1
            sheet1.update_title("Orders")
        except:
            pass
    
    def _get_or_create_sheets(self):
        """Получение или создание необходимых листов"""
        if not self.spreadsheet:
            return
        
        # Лист заказов
        try:
            self.orders_sheet = self.spreadsheet.worksheet("Orders")
        except gspread.WorksheetNotFound:
            self.orders_sheet = self.spreadsheet.add_worksheet(title="Orders", rows="1000", cols="15")
            self._setup_orders_headers()
        
        # Лист пользователей
        try:
            self.users_sheet = self.spreadsheet.worksheet("Users")
        except gspread.WorksheetNotFound:
            self.users_sheet = self.spreadsheet.add_worksheet(title="Users", rows="1000", cols="10")
            self._setup_users_headers()
        
        # Лист аналитики
        try:
            self.analytics_sheet = self.spreadsheet.worksheet("Analytics")
        except gspread.WorksheetNotFound:
            self.analytics_sheet = self.spreadsheet.add_worksheet(title="Analytics", rows="100", cols="10")
            self._setup_analytics_headers()
    
    def _get_or_create_sheet(self, sheet_name: str):
        """Получение или создание листа по имени"""
        if not self.spreadsheet:
            return None
        
        try:
            return self.spreadsheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            return self.spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="15")
    
    def _setup_orders_headers(self):
        """Настройка заголовков для листа заказов"""
        if not self.orders_sheet:
            return
        
        headers = [
            "Order ID", "User ID", "Username", "Status", "Supplier", 
            "Total Amount", "Created Date", "Updated Date", "Tracking Number",
            "Items Count", "Items Details", "Notes", "Estimated Delivery", 
            "Language", "Last Updated"
        ]
        
        self.orders_sheet.insert_row(headers, 1)
        
        # Форматирование заголовков
        self.orders_sheet.format('A1:O1', {
            "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 1.0},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}}
        })
    
    def _setup_users_headers(self):
        """Настройка заголовков для листа пользователей"""
        if not self.users_sheet:
            return
        
        headers = [
            "User ID", "Username", "First Name", "Last Name", "Language",
            "First Interaction", "Last Activity", "Orders Count", "Total Spent", "Status"
        ]
        
        self.users_sheet.insert_row(headers, 1)
        
        # Форматирование заголовков
        self.users_sheet.format('A1:J1', {
            "backgroundColor": {"red": 0.2, "green": 0.8, "blue": 0.2},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}}
        })
    
    def _setup_analytics_headers(self):
        """Настройка заголовков для листа аналитики"""
        if not self.analytics_sheet:
            return
        
        headers = [
            "Date", "Total Orders", "Pending Orders", "Confirmed Orders",
            "Production Orders", "Shipped Orders", "Delivered Orders", 
            "Cancelled Orders", "Total Revenue", "Active Users"
        ]
        
        self.analytics_sheet.insert_row(headers, 1)
        
        # Форматирование заголовков
        self.analytics_sheet.format('A1:J1', {
            "backgroundColor": {"red": 1.0, "green": 0.6, "blue": 0.2},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}}
        })
    
    def is_connected(self) -> bool:
        """Проверка подключения к Google Sheets"""
        return self.gc is not None and self.spreadsheet is not None
    
    def sync_order(self, order: Order, user_info: Dict = None):
        """Синхронизация заказа с Google Sheets"""
        if not self.is_connected():
            print(f"Google Sheets not connected, skipping order sync for {order.order_id}")
            return False
        
        try:
            print(f"Syncing order {order.order_id}...")
            # Поиск существующей записи
            existing_row = self._find_order_row(order.order_id)
            
            # Подготовка данных
            order_data = self._prepare_order_data(order, user_info)
            
            if existing_row:
                # Обновление существующей записи
                self.orders_sheet.update(f'A{existing_row}:O{existing_row}', [order_data])
                print(f"Updated order {order.order_id} in row {existing_row}")
            else:
                # Добавление новой записи
                self.orders_sheet.append_row(order_data)
                print(f"Added new order {order.order_id}")
            
            return True
            
        except Exception as e:
            print(f"Error syncing order {order.order_id}: {e}")
            return False
    
    def _find_order_row(self, order_id: str) -> Optional[int]:
        """Поиск строки заказа по ID"""
        if not self.orders_sheet:
            return None
        
        try:
            # Получаем все значения в колонке A (Order ID)
            order_ids = self.orders_sheet.col_values(1)
            
            for i, existing_id in enumerate(order_ids[1:], start=2):  # Пропускаем заголовок
                if existing_id == order_id:
                    return i
            
            return None
            
        except Exception as e:
            print(f"Error finding order: {e}")
            return None
    
    def _prepare_order_data(self, order: Order, user_info: Dict = None) -> List[str]:
        """Подготовка данных заказа для Google Sheets"""
        # Подготовка деталей товаров
        items_details = []
        for item in order.items:
            items_details.append(f"{item.product_name} x{item.quantity} (${item.unit_price})")
        
        items_str = "; ".join(items_details)
        
        # Получение информации о пользователе
        username = user_info.get('username', '') if user_info else ''
        language = user_info.get('language', 'en') if user_info else 'en'
        
        return [
            order.order_id,
            str(order.user_id),
            username,
            order.status.value,
            order.supplier,
            f"${order.total_amount:.2f}",
            order.created_date.strftime('%Y-%m-%d %H:%M:%S'),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            order.tracking_number or '',
            str(len(order.items)),
            items_str,
            order.notes,
            order.estimated_delivery.strftime('%Y-%m-%d'),
            language,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ]
    
    def sync_user_activity(self, user_id: int, user_info: Dict):
        """Синхронизация активности пользователя"""
        if not self.is_connected():
            print(f"Google Sheets not connected, skipping user sync for {user_id}")
            return False
        
        try:
            print(f"Syncing user activity for {user_id}...")
            # Поиск существующей записи пользователя
            existing_row = self._find_user_row(user_id)
            
            # Подготовка данных пользователя
            user_data = self._prepare_user_data(user_id, user_info)
            
            if existing_row:
                # Обновление существующей записи
                self.users_sheet.update(f'A{existing_row}:J{existing_row}', [user_data])
                print(f"Updated user {user_id} in row {existing_row}")
            else:
                # Добавление новой записи
                self.users_sheet.append_row(user_data)
                print(f"Added new user {user_id}")
            
            return True
            
        except Exception as e:
            print(f"Error syncing user {user_id}: {e}")
            return False
    
    def _find_user_row(self, user_id: int) -> Optional[int]:
        """Поиск строки пользователя по ID"""
        if not self.users_sheet:
            return None
        
        try:
            user_ids = self.users_sheet.col_values(1)
            
            for i, existing_id in enumerate(user_ids[1:], start=2):
                if existing_id == str(user_id):
                    return i
            
            return None
            
        except Exception as e:
            print(f"Error finding user: {e}")
            return None
    
    def _prepare_user_data(self, user_id: int, user_info: Dict) -> List[str]:
        """Подготовка данных пользователя для Google Sheets"""
        return [
            str(user_id),
            user_info.get('username', ''),
            user_info.get('first_name', ''),
            user_info.get('last_name', ''),
            user_info.get('language', 'en'),
            user_info.get('first_interaction', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            str(user_info.get('orders_count', 0)),
            f"${user_info.get('total_spent', 0):.2f}",
            user_info.get('status', 'active')
        ]
    
    def update_analytics(self, analytics_data: Dict):
        """Обновление аналитики"""
        if not self.is_connected():
            return False
        
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Поиск записи за сегодня
            existing_row = self._find_analytics_row(today)
            
            analytics_row = [
                today,
                str(analytics_data.get('total_orders', 0)),
                str(analytics_data.get('pending_orders', 0)),
                str(analytics_data.get('confirmed_orders', 0)),
                str(analytics_data.get('production_orders', 0)),
                str(analytics_data.get('shipped_orders', 0)),
                str(analytics_data.get('delivered_orders', 0)),
                str(analytics_data.get('cancelled_orders', 0)),
                f"${analytics_data.get('total_revenue', 0):.2f}",
                str(analytics_data.get('active_users', 0))
            ]
            
            if existing_row:
                self.analytics_sheet.update(f'A{existing_row}:J{existing_row}', [analytics_row])
            else:
                self.analytics_sheet.append_row(analytics_row)
            
            return True
            
        except Exception as e:
            print(f"Error updating analytics: {e}")
            return False
    
    def _find_analytics_row(self, date: str) -> Optional[int]:
        """Поиск строки аналитики по дате"""
        if not self.analytics_sheet:
            return None
        
        try:
            dates = self.analytics_sheet.col_values(1)
            
            for i, existing_date in enumerate(dates[1:], start=2):
                if existing_date == date:
                    return i
            
            return None
            
        except Exception as e:
            print(f"Error finding analytics: {e}")
            return None
    
    def get_spreadsheet_url(self) -> Optional[str]:
        """Получение URL таблицы"""
        if not self.spreadsheet:
            return None
        
        return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet.id}"
