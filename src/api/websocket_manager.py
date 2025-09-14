"""
WebSocket Manager for Real-time Warehouse Updates

Provides real-time updates for:
- Temperature readings
- Inventory movements
- Alert notifications
- Shelf utilization changes
"""

from typing import Dict, List, Set
from fastapi import WebSocket
import asyncio
import logging
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of real-time events"""

    TEMPERATURE_UPDATE = "temperature_update"
    INVENTORY_MOVEMENT = "inventory_movement"
    ALERT_TRIGGERED = "alert_triggered"
    SHELF_UPDATE = "shelf_update"
    MEDICATION_EXPIRY = "medication_expiry"
    CAPACITY_WARNING = "capacity_warning"


class ConnectionManager:
    """Manages WebSocket connections and broadcasting"""

    def __init__(self):
        # Store active connections by subscription type
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "all": set(),
            "temperature": set(),
            "inventory": set(),
            "alerts": set(),
            "shelf": set(),
        }
        self.connection_metadata: Dict[WebSocket, Dict] = {}

    async def connect(
        self, websocket: WebSocket, client_id: str, subscriptions: List[str] = None
    ):
        """Accept new WebSocket connection"""
        await websocket.accept()

        # Add to general connections
        self.active_connections["all"].add(websocket)

        # Add to specific subscription channels
        if subscriptions:
            for sub in subscriptions:
                if sub in self.active_connections:
                    self.active_connections[sub].add(websocket)

        # Store metadata
        self.connection_metadata[websocket] = {
            "client_id": client_id,
            "connected_at": datetime.now().isoformat(),
            "subscriptions": subscriptions or ["all"],
        }

        logger.info(f"Client {client_id} connected with subscriptions: {subscriptions}")

        # Send welcome message
        await self.send_personal_message(
            websocket,
            {
                "type": "connection_established",
                "client_id": client_id,
                "timestamp": datetime.now().isoformat(),
                "subscriptions": subscriptions or ["all"],
            },
        )

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        # Remove from all subscription channels
        for channel in self.active_connections.values():
            channel.discard(websocket)

        # Get client info for logging
        client_info = self.connection_metadata.get(websocket, {})
        client_id = client_info.get("client_id", "unknown")

        # Remove metadata
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]

        logger.info(f"Client {client_id} disconnected")

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """Send message to specific connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast(self, message: dict, channel: str = "all"):
        """Broadcast message to all connections in a channel"""
        connections = self.active_connections.get(channel, set())
        disconnected = set()

        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.add(connection)

        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_temperature_update(
        self, aisle_id: int, temperature: float, humidity: float = None
    ):
        """Broadcast temperature update"""
        message = {
            "type": EventType.TEMPERATURE_UPDATE.value,
            "data": {
                "aisle_id": aisle_id,
                "temperature": temperature,
                "humidity": humidity,
                "timestamp": datetime.now().isoformat(),
            },
        }
        await self.broadcast(message, "temperature")
        await self.broadcast(message, "all")

    async def broadcast_inventory_movement(
        self, med_id: int, from_shelf: int, to_shelf: int, quantity: int
    ):
        """Broadcast inventory movement"""
        message = {
            "type": EventType.INVENTORY_MOVEMENT.value,
            "data": {
                "med_id": med_id,
                "from_shelf": from_shelf,
                "to_shelf": to_shelf,
                "quantity": quantity,
                "timestamp": datetime.now().isoformat(),
            },
        }
        await self.broadcast(message, "inventory")
        await self.broadcast(message, "all")

    async def broadcast_alert(
        self, alert_type: str, severity: str, location: str, message_text: str
    ):
        """Broadcast alert notification"""
        message = {
            "type": EventType.ALERT_TRIGGERED.value,
            "data": {
                "alert_type": alert_type,
                "severity": severity,
                "location": location,
                "message": message_text,
                "timestamp": datetime.now().isoformat(),
            },
        }
        await self.broadcast(message, "alerts")
        await self.broadcast(message, "all")

    async def broadcast_shelf_update(
        self, shelf_id: int, utilization: float, medications_count: int
    ):
        """Broadcast shelf utilization update"""
        message = {
            "type": EventType.SHELF_UPDATE.value,
            "data": {
                "shelf_id": shelf_id,
                "utilization_percent": utilization,
                "medications_count": medications_count,
                "timestamp": datetime.now().isoformat(),
            },
        }
        await self.broadcast(message, "shelf")
        await self.broadcast(message, "all")

    def get_connection_stats(self):
        """Get statistics about active connections"""
        stats = {
            "total_connections": len(self.connection_metadata),
            "connections_by_channel": {
                channel: len(connections)
                for channel, connections in self.active_connections.items()
            },
            "clients": [
                {
                    "client_id": meta["client_id"],
                    "connected_at": meta["connected_at"],
                    "subscriptions": meta["subscriptions"],
                }
                for meta in self.connection_metadata.values()
            ],
        }
        return stats


# Global connection manager instance
ws_manager = ConnectionManager()


class WarehouseEventSimulator:
    """Simulates warehouse events for testing WebSocket functionality"""

    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self.running = False

    async def start_simulation(self):
        """Start simulating warehouse events"""
        self.running = True
        logger.info("Starting warehouse event simulation")

        while self.running:
            try:
                # Simulate temperature readings every 10 seconds
                if asyncio.get_event_loop().time() % 10 < 1:
                    await self._simulate_temperature_reading()

                # Simulate inventory movements every 30 seconds
                if asyncio.get_event_loop().time() % 30 < 1:
                    await self._simulate_inventory_movement()

                # Simulate alerts every 60 seconds
                if asyncio.get_event_loop().time() % 60 < 1:
                    await self._simulate_alert()

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in event simulation: {e}")

    async def stop_simulation(self):
        """Stop simulating events"""
        self.running = False
        logger.info("Stopped warehouse event simulation")

    async def _simulate_temperature_reading(self):
        """Simulate temperature reading from sensors"""
        import random

        aisle_id = random.randint(1, 6)
        temperature = round(random.uniform(18, 24), 1)
        humidity = round(random.uniform(40, 60), 1)

        await self.manager.broadcast_temperature_update(aisle_id, temperature, humidity)

    async def _simulate_inventory_movement(self):
        """Simulate inventory movement"""
        import random

        med_id = random.randint(1, 50)
        from_shelf = random.randint(1, 48)
        to_shelf = random.randint(1, 48)
        quantity = random.randint(1, 20)

        if from_shelf != to_shelf:
            await self.manager.broadcast_inventory_movement(
                med_id, from_shelf, to_shelf, quantity
            )

    async def _simulate_alert(self):
        """Simulate various alerts"""
        import random

        alert_types = [
            ("temperature", "warning", "Aisle A", "Temperature out of range: 26°C"),
            ("expiry", "critical", "Shelf B3", "Medication expires in 3 days"),
            ("capacity", "info", "Shelf C5", "Shelf at 95% capacity"),
            ("expiry", "warning", "Shelf A2", "Medication expires in 15 days"),
        ]

        alert = random.choice(alert_types)
        await self.manager.broadcast_alert(*alert)


# Create simulator instance
event_simulator = WarehouseEventSimulator(ws_manager)
