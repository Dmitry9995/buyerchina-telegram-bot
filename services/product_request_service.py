#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Product Request Service
Сервис для обработки запросов на поиск товаров через менеджера
"""

import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
from services.google_sheets_service import GoogleSheetsService

@dataclass
class ProductRequest:
    request_id: str
    user_id: int
    username: str
    request_type: str  # 'text' или 'image'
    description: str
    image_url: Optional[str] = None
    status: str = 'pending'  # pending, processing, completed, cancelled
    created_date: str = None
    manager_response: str = None
    estimated_price: str = None
    supplier_info: str = None
    
    def __post_init__(self):
        if self.created_date is None:
            self.created_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

class ProductRequestService:
    def __init__(self, google_sheets_service: GoogleSheetsService = None):
        self.google_sheets_service = google_sheets_service
        self.pending_requests = {}  # Локальное хранение для быстрого доступа
        
    def create_product_request(self, user_id: int, username: str, description: str, 
                             image_url: Optional[str] = None) -> ProductRequest:
        """Создать новый запрос на поиск товара"""
        request_id = str(uuid.uuid4())[:8]  # Короткий ID для удобства
        
        request_type = 'image' if image_url else 'text'
        
        request = ProductRequest(
            request_id=request_id,
            user_id=user_id,
            username=username,
            request_type=request_type,
            description=description,
            image_url=image_url
        )
        
        # Сохраняем локально
        self.pending_requests[request_id] = request
        
        # Отправляем в Google Sheets
        if self.google_sheets_service and self.google_sheets_service.is_connected():
            self._sync_request_to_sheets(request)
        
        return request
    
    def _sync_request_to_sheets(self, request: ProductRequest):
        """Синхронизировать запрос с Google Sheets"""
        try:
            # Получаем или создаем лист для запросов товаров
            sheet = self.google_sheets_service._get_or_create_sheet("Product Requests")
            
            # Заголовки для листа запросов
            headers = [
                "Request ID", "User ID", "Username", "Request Type", "Description", 
                "Image URL", "Status", "Created Date", "Manager Response", 
                "Estimated Price", "Supplier Info", "Response Date"
            ]
            
            # Проверяем и устанавливаем заголовки
            if not sheet.row_values(1):
                sheet.update('A1:L1', [headers])
            
            # Добавляем новый запрос
            row_data = [
                request.request_id,
                str(request.user_id),
                request.username,
                request.request_type,
                request.description,
                request.image_url or '',
                request.status,
                request.created_date,
                request.manager_response or '',
                request.estimated_price or '',
                request.supplier_info or '',
                ''  # Response Date - заполнится при ответе менеджера
            ]
            
            # Находим следующую пустую строку
            all_values = sheet.get_all_values()
            next_row = len(all_values) + 1
            
            # Добавляем данные
            range_name = f'A{next_row}:L{next_row}'
            sheet.update(range_name, [row_data])
            
            print(f"Request {request.request_id} added to Google Sheets")
            
        except Exception as e:
            print(f"Error syncing request to Google Sheets: {e}")
    
    def get_user_requests(self, user_id: int) -> list:
        """Получить все запросы пользователя"""
        user_requests = []
        for request in self.pending_requests.values():
            if request.user_id == user_id:
                user_requests.append(request)
        
        return sorted(user_requests, key=lambda x: x.created_date, reverse=True)
    
    def get_request_status(self, request_id: str) -> Optional[ProductRequest]:
        """Получить статус запроса"""
        return self.pending_requests.get(request_id)
    
    def format_request_confirmation(self, request: ProductRequest, language_service=None, user_id=None) -> str:
        """Форматировать подтверждение запроса"""
        if language_service and user_id:
            lang = language_service.get_user_language(user_id)
            if lang == 'ru':
                header = "✅ **Запрос на поиск товара отправлен**"
                request_id_label = "ID запроса:"
                type_label = "Тип запроса:"
                description_label = "Описание:"
                status_label = "Статус:"
                manager_note = "📋 **Ваш запрос передан менеджеру**\n\n" \
                              "🕐 Менеджер обработает ваш запрос и предоставит:\n" \
                              "• Подходящие товары с ценами\n" \
                              "• Информацию о поставщиках\n" \
                              "• Условия заказа и доставки\n\n" \
                              "⏱️ Обычно ответ приходит в течение 1-2 часов в рабочее время."
            else:
                header = "✅ **Product Search Request Submitted**"
                request_id_label = "Request ID:"
                type_label = "Request Type:"
                description_label = "Description:"
                status_label = "Status:"
                manager_note = "📋 **Your request has been sent to our manager**\n\n" \
                              "🕐 Our manager will process your request and provide:\n" \
                              "• Suitable products with prices\n" \
                              "• Supplier information\n" \
                              "• Order and shipping terms\n\n" \
                              "⏱️ Response usually comes within 1-2 hours during business hours."
        else:
            header = "✅ **Product Search Request Submitted**"
            request_id_label = "Request ID:"
            type_label = "Request Type:"
            description_label = "Description:"
            status_label = "Status:"
            manager_note = "📋 **Your request has been sent to our manager**\n\n" \
                          "🕐 Our manager will process your request and provide:\n" \
                          "• Suitable products with prices\n" \
                          "• Supplier information\n" \
                          "• Order and shipping terms\n\n" \
                          "⏱️ Response usually comes within 1-2 hours during business hours."
        
        message = f"{header}\n\n"
        message += f"🆔 **{request_id_label}** `{request.request_id}`\n"
        message += f"📝 **{type_label}** {request.request_type.title()}\n"
        message += f"📋 **{description_label}** {request.description}\n"
        
        if request.image_url:
            message += f"🖼️ **Изображение:** Прикреплено\n"
        
        message += f"📊 **{status_label}** {request.status.title()}\n\n"
        message += manager_note
        
        return message
    
    def format_user_requests(self, requests: list, language_service=None, user_id=None) -> str:
        """Форматировать список запросов пользователя"""
        if not requests:
            if language_service and user_id:
                lang = language_service.get_user_language(user_id)
                if lang == 'ru':
                    return "📋 У вас пока нет запросов на поиск товаров."
                else:
                    return "📋 You don't have any product search requests yet."
            return "📋 You don't have any product search requests yet."
        
        if language_service and user_id:
            lang = language_service.get_user_language(user_id)
            if lang == 'ru':
                header = f"📋 **Ваши запросы на поиск товаров** ({len(requests)})"
            else:
                header = f"📋 **Your Product Search Requests** ({len(requests)})"
        else:
            header = f"📋 **Your Product Search Requests** ({len(requests)})"
        
        message = f"{header}\n\n"
        
        for i, request in enumerate(requests[:10], 1):  # Показываем последние 10
            status_emoji = {
                'pending': '🕐',
                'processing': '⚙️',
                'completed': '✅',
                'cancelled': '❌'
            }.get(request.status, '❓')
            
            message += f"{status_emoji} **{request.request_id}** - {request.description[:50]}...\n"
            message += f"   📅 {request.created_date} | 📊 {request.status.title()}\n\n"
        
        return message
