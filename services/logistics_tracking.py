from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

class ShipmentStatus(Enum):
    PREPARING = "preparing"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    CUSTOMS = "customs"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    EXCEPTION = "exception"

@dataclass
class TrackingEvent:
    timestamp: datetime
    location: str
    status: ShipmentStatus
    description: str

@dataclass
class Shipment:
    tracking_number: str
    carrier: str
    origin: str
    destination: str
    current_status: ShipmentStatus
    events: List[TrackingEvent]
    estimated_delivery: datetime
    weight: Optional[str] = None
    dimensions: Optional[str] = None

class LogisticsTrackingService:
    def __init__(self):
        self.shipments: Dict[str, Shipment] = {}
        self._create_mock_shipments()
    
    def _create_mock_shipments(self):
        """Create mock shipments for demonstration"""
        # Mock shipment 1
        events1 = [
            TrackingEvent(
                timestamp=datetime.now() - timedelta(days=3),
                location="Shenzhen, China",
                status=ShipmentStatus.PICKED_UP,
                description="Package picked up from supplier"
            ),
            TrackingEvent(
                timestamp=datetime.now() - timedelta(days=2),
                location="Guangzhou, China",
                status=ShipmentStatus.IN_TRANSIT,
                description="In transit to international hub"
            ),
            TrackingEvent(
                timestamp=datetime.now() - timedelta(days=1),
                location="Hong Kong",
                status=ShipmentStatus.CUSTOMS,
                description="Customs clearance in progress"
            )
        ]
        
        shipment1 = Shipment(
            tracking_number="SF1234567890",
            carrier="SF Express",
            origin="Shenzhen, China",
            destination="New York, USA",
            current_status=ShipmentStatus.CUSTOMS,
            events=events1,
            estimated_delivery=datetime.now() + timedelta(days=5),
            weight="2.5 kg",
            dimensions="30x20x15 cm"
        )
        
        self.shipments["SF1234567890"] = shipment1
        
        # Mock shipment 2
        events2 = [
            TrackingEvent(
                timestamp=datetime.now() - timedelta(days=7),
                location="Guangzhou, China",
                status=ShipmentStatus.PICKED_UP,
                description="Package collected from warehouse"
            ),
            TrackingEvent(
                timestamp=datetime.now() - timedelta(days=5),
                location="Shanghai, China",
                status=ShipmentStatus.IN_TRANSIT,
                description="Departed from sorting facility"
            ),
            TrackingEvent(
                timestamp=datetime.now() - timedelta(days=3),
                location="Los Angeles, USA",
                status=ShipmentStatus.CUSTOMS,
                description="Arrived at destination country"
            ),
            TrackingEvent(
                timestamp=datetime.now() - timedelta(days=1),
                location="Los Angeles, USA",
                status=ShipmentStatus.OUT_FOR_DELIVERY,
                description="Out for delivery"
            )
        ]
        
        shipment2 = Shipment(
            tracking_number="DHL9876543210",
            carrier="DHL Express",
            origin="Guangzhou, China",
            destination="Los Angeles, USA",
            current_status=ShipmentStatus.OUT_FOR_DELIVERY,
            events=events2,
            estimated_delivery=datetime.now() + timedelta(days=1),
            weight="5.2 kg",
            dimensions="40x30x25 cm"
        )
        
        self.shipments["DHL9876543210"] = shipment2
    
    def track_shipment(self, tracking_number: str) -> Optional[Shipment]:
        """Track a shipment by tracking number"""
        return self.shipments.get(tracking_number.upper())
    
    def format_tracking_info(self, shipment: Shipment, language_service=None, user_id=None) -> str:
        """Format shipment tracking information"""
        status_emoji = self._get_status_emoji(shipment.current_status)
        
        if language_service and user_id:
            header = language_service.get_text(user_id, 'shipment_tracking')
            status_label = language_service.get_text(user_id, 'status')
            carrier_label = language_service.get_text(user_id, 'carrier')
            origin_label = language_service.get_text(user_id, 'origin')
            destination_label = language_service.get_text(user_id, 'destination')
            weight_label = language_service.get_text(user_id, 'weight')
            dimensions_label = language_service.get_text(user_id, 'dimensions')
            est_delivery_label = language_service.get_text(user_id, 'est_delivery')
            tracking_label = language_service.get_text(user_id, 'tracking')
            history_label = language_service.get_text(user_id, 'tracking_history')
        else:
            header = "📦 **Shipment Tracking**"
            status_label = "Status:"
            carrier_label = "Carrier:"
            origin_label = "Origin:"
            destination_label = "Destination:"
            weight_label = "Weight:"
            dimensions_label = "Dimensions:"
            est_delivery_label = "Est. Delivery:"
            tracking_label = "Tracking #:"
            history_label = "📍 Tracking History:"
        
        message = f"{header}\n\n"
        message += f"**{tracking_label}** {shipment.tracking_number}\n"
        message += f"**{carrier_label}** {shipment.carrier}\n"
        message += f"**{status_label}** {shipment.current_status.value.replace('_', ' ').title()} {status_emoji}\n"
        message += f"**{origin_label}** {shipment.origin}\n"
        message += f"**{destination_label}** {shipment.destination}\n"
        message += f"**{est_delivery_label}** {shipment.estimated_delivery.strftime('%Y-%m-%d')}\n"
        
        if shipment.weight:
            message += f"**{weight_label}** {shipment.weight}\n"
        if shipment.dimensions:
            message += f"**{dimensions_label}** {shipment.dimensions}\n"
        
        message += f"\n**{history_label}**\n"
        
        # Sort events by timestamp (newest first)
        sorted_events = sorted(shipment.events, key=lambda x: x.timestamp, reverse=True)
        
        for event in sorted_events:
            event_emoji = self._get_status_emoji(event.status)
            message += f"\n{event_emoji} **{event.timestamp.strftime('%m/%d %H:%M')}** - {event.location}\n"
            message += f"   {event.description}\n"
        
        return message
    
    def get_delivery_estimate(self, tracking_number: str) -> Optional[str]:
        """Get delivery estimate for a shipment"""
        shipment = self.track_shipment(tracking_number)
        if not shipment:
            return None
        
        days_remaining = (shipment.estimated_delivery - datetime.now()).days
        
        if days_remaining < 0:
            return "📦 Package should have been delivered"
        elif days_remaining == 0:
            return "📦 Delivery expected today"
        elif days_remaining == 1:
            return "📦 Delivery expected tomorrow"
        else:
            return f"📦 Delivery expected in {days_remaining} days"
    
    def _get_status_emoji(self, status: ShipmentStatus) -> str:
        """Get emoji for shipment status"""
        status_emojis = {
            ShipmentStatus.PREPARING: "📋",
            ShipmentStatus.PICKED_UP: "📦",
            ShipmentStatus.IN_TRANSIT: "🚛",
            ShipmentStatus.CUSTOMS: "🛃",
            ShipmentStatus.OUT_FOR_DELIVERY: "🚚",
            ShipmentStatus.DELIVERED: "✅",
            ShipmentStatus.EXCEPTION: "⚠️"
        }
        return status_emojis.get(status, "❓")
    
    def get_all_active_shipments(self) -> List[Shipment]:
        """Get all shipments that are not yet delivered"""
        return [
            shipment for shipment in self.shipments.values()
            if shipment.current_status != ShipmentStatus.DELIVERED
        ]
