from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PRODUCTION = "production"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

@dataclass
class OrderItem:
    product_name: str
    quantity: int
    unit_price: float
    total_price: float

@dataclass
class Order:
    order_id: str
    user_id: int
    items: List[OrderItem]
    supplier: str
    status: OrderStatus
    created_date: datetime
    estimated_delivery: datetime
    total_amount: float
    tracking_number: Optional[str] = None
    notes: str = ""

class OrderManagementService:
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.user_orders: Dict[int, List[str]] = {}
        
        # Mock orders for demonstration
        self._create_mock_orders()
    
    def _create_mock_orders(self):
        """Create some mock orders for demonstration"""
        mock_order = Order(
            order_id="ORD-2024-001",
            user_id=123456789,  # Replace with actual user ID
            items=[
                OrderItem("Wireless Bluetooth Headphones", 500, 10.50, 5250.00),
                OrderItem("USB-C Cable 1m", 1000, 1.00, 1000.00)
            ],
            supplier="Shenzhen Audio Tech Co.",
            status=OrderStatus.PRODUCTION,
            created_date=datetime.now() - timedelta(days=5),
            estimated_delivery=datetime.now() + timedelta(days=10),
            total_amount=6250.00,
            tracking_number="SF1234567890",
            notes="Rush order for electronics store"
        )
        
        self.orders[mock_order.order_id] = mock_order
        if mock_order.user_id not in self.user_orders:
            self.user_orders[mock_order.user_id] = []
        self.user_orders[mock_order.user_id].append(mock_order.order_id)
    
    def create_order(self, user_id: int, items: List[OrderItem], supplier: str, notes: str = "", google_sheets_service=None) -> Order:
        """Create a new order"""
        order_id = f"ORD-{datetime.now().strftime('%Y%m%d')}-{len(self.orders) + 1:03d}"
        total_amount = sum(item.total_price for item in items)
        
        order = Order(
            order_id=order_id,
            user_id=user_id,
            items=items,
            supplier=supplier,
            status=OrderStatus.PENDING,
            created_date=datetime.now(),
            estimated_delivery=datetime.now() + timedelta(days=15),
            total_amount=total_amount,
            notes=notes
        )
        
        self.orders[order_id] = order
        
        if user_id not in self.user_orders:
            self.user_orders[user_id] = []
        self.user_orders[user_id].append(order_id)
        
        # Синхронизация с Google Sheets
        if google_sheets_service and google_sheets_service.is_connected():
            google_sheets_service.sync_order(order)
        
        return order_id
    
    def get_user_orders(self, user_id: int) -> List[Order]:
        """Get all orders for a specific user"""
        if user_id not in self.user_orders:
            return []
        
        return [self.orders[order_id] for order_id in self.user_orders[user_id]]
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get a specific order by ID"""
        return self.orders.get(order_id)
    
    def update_order_status(self, order_id: str, status: OrderStatus, google_sheets_service=None, tracking_number: str = None) -> bool:
        """Update order status"""
        if order_id not in self.orders:
            return False
        
        self.orders[order_id].status = status
        if tracking_number:
            self.orders[order_id].tracking_number = tracking_number
        
        # Синхронизация с Google Sheets
        if google_sheets_service and google_sheets_service.is_connected():
            google_sheets_service.sync_order(self.orders[order_id])
        
        return True
    
    def format_order_summary(self, orders: List[Order], language_service=None, user_id=None) -> str:
        """Format orders into a readable summary"""
        if not orders:
            if language_service and user_id:
                return language_service.get_text(user_id, 'no_orders')
            return "📦 No orders found.\n\n💡 Start by searching for products and contact us to place your first order!"
        
        if language_service and user_id:
            header = language_service.get_text(user_id, 'your_orders', count=len(orders))
            supplier_label = language_service.get_text(user_id, 'supplier')
            total_label = language_service.get_text(user_id, 'total')
            created_label = language_service.get_text(user_id, 'created')
            tracking_label = language_service.get_text(user_id, 'tracking')
            est_delivery_label = language_service.get_text(user_id, 'est_delivery')
        else:
            header = f"📦 **Your Orders ({len(orders)} total)**"
            supplier_label = "Supplier:"
            total_label = "Total:"
            created_label = "Created:"
            tracking_label = "Tracking:"
            est_delivery_label = "Est. Delivery:"
        
        message = f"{header}\n\n"
        
        for order in orders[-5:]:  # Show last 5 orders
            status_emoji = self._get_status_emoji(order.status)
            message += f"**{order.order_id}** {status_emoji}\n"
            message += f"🏭 {supplier_label} {order.supplier}\n"
            message += f"💰 {total_label} ${order.total_amount:,.2f}\n"
            message += f"📅 {created_label} {order.created_date.strftime('%Y-%m-%d')}\n"
            
            if order.tracking_number:
                message += f"📦 {tracking_label} {order.tracking_number}\n"
            
            message += f"🚚 {est_delivery_label} {order.estimated_delivery.strftime('%Y-%m-%d')}\n\n"
        
        return message
    
    def format_order_details(self, order: Order) -> str:
        """Format detailed order information"""
        status_emoji = self._get_status_emoji(order.status)
        
        message = f"📋 **Order Details**\n\n"
        message += f"**Order ID:** {order.order_id}\n"
        message += f"**Status:** {order.status.value.title()} {status_emoji}\n"
        message += f"**Supplier:** {order.supplier}\n"
        message += f"**Created:** {order.created_date.strftime('%Y-%m-%d %H:%M')}\n"
        message += f"**Est. Delivery:** {order.estimated_delivery.strftime('%Y-%m-%d')}\n"
        
        if order.tracking_number:
            message += f"**Tracking:** {order.tracking_number}\n"
        
        message += f"\n**Items:**\n"
        for item in order.items:
            message += f"• {item.product_name}\n"
            message += f"  Qty: {item.quantity} × ${item.unit_price:.2f} = ${item.total_price:.2f}\n"
        
        message += f"\n**Total Amount:** ${order.total_amount:,.2f}\n"
        
        if order.notes:
            message += f"\n**Notes:** {order.notes}\n"
        
        return message
    
    def _get_status_emoji(self, status: OrderStatus) -> str:
        """Get emoji for order status"""
        status_emojis = {
            OrderStatus.PENDING: "⏳",
            OrderStatus.CONFIRMED: "✅",
            OrderStatus.PRODUCTION: "🏭",
            OrderStatus.SHIPPED: "🚚",
            OrderStatus.DELIVERED: "📦",
            OrderStatus.CANCELLED: "❌"
        }
        return status_emojis.get(status, "❓")
