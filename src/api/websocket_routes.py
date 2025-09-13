"""
WebSocket Routes for Real-time Warehouse Updates

Provides WebSocket endpoints for real-time communication
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from typing import List, Optional
import json
import asyncio
import logging
from src.api.websocket_manager import ws_manager, event_simulator

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/warehouse")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str = Query(...),
    subscriptions: Optional[str] = Query(None, description="Comma-separated list of subscriptions")
):
    """
    WebSocket endpoint for real-time warehouse updates

    Subscriptions:
    - all: Receive all updates (default)
    - temperature: Temperature sensor updates
    - inventory: Inventory movement updates
    - alerts: Alert notifications
    - shelf: Shelf utilization updates

    Example connection:
    ws://localhost:8000/ws/warehouse?client_id=client123&subscriptions=temperature,alerts
    """
    # Parse subscriptions
    sub_list = subscriptions.split(",") if subscriptions else ["all"]

    # Connect client
    await ws_manager.connect(websocket, client_id, sub_list)

    try:
        # Keep connection alive and handle incoming messages
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                await handle_client_message(websocket, message)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"Error handling client message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info(f"Client {client_id} disconnected normally")
    except Exception as e:
        ws_manager.disconnect(websocket)
        logger.error(f"Client {client_id} disconnected with error: {e}")


async def handle_client_message(websocket: WebSocket, message: dict):
    """Handle incoming messages from WebSocket clients"""

    msg_type = message.get("type")

    if msg_type == "ping":
        # Respond to ping with pong
        await websocket.send_json({
            "type": "pong",
            "timestamp": message.get("timestamp")
        })

    elif msg_type == "subscribe":
        # Add subscription to existing connection
        channels = message.get("channels", [])
        for channel in channels:
            if channel in ws_manager.active_connections:
                ws_manager.active_connections[channel].add(websocket)

        await websocket.send_json({
            "type": "subscription_updated",
            "channels": channels,
            "status": "subscribed"
        })

    elif msg_type == "unsubscribe":
        # Remove subscription from connection
        channels = message.get("channels", [])
        for channel in channels:
            if channel in ws_manager.active_connections:
                ws_manager.active_connections[channel].discard(websocket)

        await websocket.send_json({
            "type": "subscription_updated",
            "channels": channels,
            "status": "unsubscribed"
        })

    elif msg_type == "request_status":
        # Send current connection status
        metadata = ws_manager.connection_metadata.get(websocket, {})
        await websocket.send_json({
            "type": "status",
            "client_id": metadata.get("client_id"),
            "connected_at": metadata.get("connected_at"),
            "subscriptions": metadata.get("subscriptions", [])
        })

    else:
        # Unknown message type
        await websocket.send_json({
            "type": "error",
            "message": f"Unknown message type: {msg_type}"
        })


@router.get("/ws/connections")
async def get_websocket_connections():
    """Get information about active WebSocket connections"""
    return ws_manager.get_connection_stats()


@router.post("/ws/broadcast/temperature")
async def broadcast_temperature_update(
    aisle_id: int,
    temperature: float,
    humidity: Optional[float] = None
):
    """
    Manually broadcast a temperature update to all subscribed clients

    Used for testing or manual sensor readings
    """
    await ws_manager.broadcast_temperature_update(aisle_id, temperature, humidity)
    return {
        "success": True,
        "message": "Temperature update broadcasted",
        "data": {
            "aisle_id": aisle_id,
            "temperature": temperature,
            "humidity": humidity
        }
    }


@router.post("/ws/broadcast/movement")
async def broadcast_movement(
    med_id: int,
    from_shelf: int,
    to_shelf: int,
    quantity: int
):
    """
    Broadcast an inventory movement to all subscribed clients

    Automatically called when medications are moved
    """
    await ws_manager.broadcast_inventory_movement(med_id, from_shelf, to_shelf, quantity)
    return {
        "success": True,
        "message": "Movement broadcasted",
        "data": {
            "med_id": med_id,
            "from_shelf": from_shelf,
            "to_shelf": to_shelf,
            "quantity": quantity
        }
    }


@router.post("/ws/broadcast/alert")
async def broadcast_alert(
    alert_type: str,
    severity: str,
    location: str,
    message: str
):
    """
    Broadcast an alert to all subscribed clients

    Alert types: temperature, expiry, capacity, security
    Severity: critical, warning, info
    """
    await ws_manager.broadcast_alert(alert_type, severity, location, message)
    return {
        "success": True,
        "message": "Alert broadcasted",
        "data": {
            "alert_type": alert_type,
            "severity": severity,
            "location": location,
            "message": message
        }
    }


@router.post("/ws/simulation/start")
async def start_event_simulation():
    """
    Start simulating warehouse events for testing

    Generates random temperature readings, movements, and alerts
    """
    if not event_simulator.running:
        asyncio.create_task(event_simulator.start_simulation())
        return {
            "success": True,
            "message": "Event simulation started"
        }
    else:
        return {
            "success": False,
            "message": "Simulation already running"
        }


@router.post("/ws/simulation/stop")
async def stop_event_simulation():
    """Stop the event simulation"""
    await event_simulator.stop_simulation()
    return {
        "success": True,
        "message": "Event simulation stopped"
    }


@router.get("/ws/simulation/status")
async def get_simulation_status():
    """Get the status of event simulation"""
    return {
        "running": event_simulator.running,
        "connections": ws_manager.get_connection_stats()
    }