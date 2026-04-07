import asyncio
import json
import logging
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for live ride tracking.
    Structure:
        ride_connections: {ride_id: {user_id: WebSocket}}
        driver_connections: {ride_id: WebSocket}  # The driver's socket
    """

    def __init__(self):
        # ride_id -> set of rider WebSocket connections
        self.ride_rider_connections: Dict[str, Dict[str, WebSocket]] = {}
        # ride_id -> driver WebSocket
        self.ride_driver_connection: Dict[str, WebSocket] = {}
        # Latest location per ride
        self.last_location: Dict[str, dict] = {}
        # Stall detection: last movement time per ride
        self.last_movement_time: Dict[str, datetime] = {}

    async def connect_driver(self, ride_id: str, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.ride_driver_connection[ride_id] = websocket
        logger.info(f"Driver {user_id} connected for ride {ride_id}")

    async def connect_rider(self, ride_id: str, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if ride_id not in self.ride_rider_connections:
            self.ride_rider_connections[ride_id] = {}
        self.ride_rider_connections[ride_id][user_id] = websocket
        logger.info(f"Rider {user_id} connected for ride {ride_id}")
        
        # Send last known location immediately if available
        if ride_id in self.last_location:
            try:
                await websocket.send_json(self.last_location[ride_id])
            except Exception:
                pass

    def disconnect_driver(self, ride_id: str):
        self.ride_driver_connection.pop(ride_id, None)
        logger.info(f"Driver disconnected from ride {ride_id}")

    def disconnect_rider(self, ride_id: str, user_id: str):
        if ride_id in self.ride_rider_connections:
            self.ride_rider_connections[ride_id].pop(user_id, None)
            if not self.ride_rider_connections[ride_id]:
                del self.ride_rider_connections[ride_id]
        logger.info(f"Rider {user_id} disconnected from ride {ride_id}")

    async def broadcast_location_to_riders(self, ride_id: str, data: dict):
        """Send driver location to all riders watching this ride."""
        self.last_location[ride_id] = data
        
        if ride_id not in self.ride_rider_connections:
            return
        
        disconnected = []
        for user_id, ws in self.ride_rider_connections[ride_id].items():
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.warning(f"Failed to send to rider {user_id}: {e}")
                disconnected.append(user_id)
        
        for uid in disconnected:
            self.ride_rider_connections[ride_id].pop(uid, None)

    async def send_alert_to_ride(self, ride_id: str, alert: dict):
        """Broadcast a safety alert to all connections for a ride."""
        alert["type"] = "safety_alert"
        
        # Send to riders
        if ride_id in self.ride_rider_connections:
            for user_id, ws in list(self.ride_rider_connections[ride_id].items()):
                try:
                    await ws.send_json(alert)
                except Exception:
                    pass
        
        # Send to driver too
        if ride_id in self.ride_driver_connection:
            try:
                await self.ride_driver_connection[ride_id].send_json(alert)
            except Exception:
                pass

    def check_stall(self, ride_id: str, lat: float, lng: float, stall_minutes: int = 5) -> bool:
        """
        Detect if vehicle has stalled (no movement for N minutes).
        Returns True if stall detected.
        """
        now = datetime.now(timezone.utc)
        last = self.last_location.get(ride_id)
        
        if last:
            last_lat = last.get("lat", 0)
            last_lng = last.get("lng", 0)
            from utils.geo import haversine_distance
            dist = haversine_distance(lat, lng, last_lat, last_lng)
            
            if dist > 0.05:  # moved more than 50m
                self.last_movement_time[ride_id] = now
                return False
            
            if ride_id in self.last_movement_time:
                elapsed = (now - self.last_movement_time[ride_id]).total_seconds() / 60
                return elapsed >= stall_minutes
        else:
            self.last_movement_time[ride_id] = now
        
        return False

    def get_rider_count(self, ride_id: str) -> int:
        return len(self.ride_rider_connections.get(ride_id, {}))


# Singleton
manager = ConnectionManager()
