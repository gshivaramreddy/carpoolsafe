import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import AsyncSessionLocal
from models.models import Ride, User
from utils.auth import get_current_user_ws
from utils.geo import detect_route_deviation
from utils.config import settings
from websocket.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/track/{ride_id}")
async def track_ride(
    websocket: WebSocket,
    ride_id: str,
    token: str = Query(...),
    role: str = Query("rider"),
):
    """
    WebSocket endpoint for live ride tracking.
    
    Drivers send location updates.
    Riders receive location updates.
    
    Query params:
        token: JWT auth token
        role: "driver" or "rider"
    """
    async with AsyncSessionLocal() as db:
        user = await get_current_user_ws(token, db)
        if not user:
            await websocket.close(code=4001, reason="Unauthorized")
            return

        # Verify ride exists
        result = await db.execute(select(Ride).where(Ride.id == ride_id))
        ride = result.scalar_one_or_none()
        if not ride:
            await websocket.close(code=4004, reason="Ride not found")
            return

    if role == "driver":
        await _handle_driver_ws(websocket, ride_id, user.id, ride)
    else:
        await _handle_rider_ws(websocket, ride_id, user.id)


async def _handle_driver_ws(websocket: WebSocket, ride_id: str, user_id: str, ride):
    """Driver sends location updates to all riders."""
    await manager.connect_driver(ride_id, user_id, websocket)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "message": "Driver tracking active",
            "ride_id": ride_id,
            "riders_watching": manager.get_rider_count(ride_id),
        })
        
        route_points = ride.route_points or []
        
        while True:
            data = await websocket.receive_json()
            
            lat = data.get("lat")
            lng = data.get("lng")
            
            if lat is None or lng is None:
                continue
            
            now = datetime.now(timezone.utc)
            
            # Update DB with latest location
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Ride)
                    .where(Ride.id == ride_id)
                    .values(
                        current_lat=lat,
                        current_lng=lng,
                        last_location_update=now,
                    )
                )
                await db.commit()
            
            # Build broadcast payload
            payload = {
                "type": "location_update",
                "ride_id": ride_id,
                "lat": lat,
                "lng": lng,
                "speed": data.get("speed"),
                "heading": data.get("heading"),
                "timestamp": now.isoformat(),
            }
            
            # Stall detection
            is_stalled = manager.check_stall(ride_id, lat, lng, settings.STALL_DETECTION_MINUTES)
            if is_stalled:
                alert = {
                    "type": "safety_alert",
                    "alert_type": "stall_detected",
                    "message": "⚠️ Vehicle appears to have stalled or stopped for extended time",
                    "lat": lat,
                    "lng": lng,
                    "timestamp": now.isoformat(),
                }
                await manager.send_alert_to_ride(ride_id, alert)
                logger.warning(f"Stall detected for ride {ride_id}")
            
            # Route deviation detection
            if route_points:
                is_deviated, deviation_km = detect_route_deviation(
                    lat, lng, route_points, settings.MAX_ROUTE_DEVIATION_KM
                )
                payload["deviation_km"] = round(deviation_km, 3)
                
                if is_deviated:
                    alert = {
                        "type": "safety_alert",
                        "alert_type": "route_deviation",
                        "message": f"⚠️ Route deviation detected: {deviation_km:.2f} km from planned route",
                        "deviation_km": round(deviation_km, 3),
                        "lat": lat,
                        "lng": lng,
                        "timestamp": now.isoformat(),
                    }
                    await manager.send_alert_to_ride(ride_id, alert)
                    logger.warning(f"Route deviation {deviation_km:.2f}km for ride {ride_id}")
            
            # Broadcast to riders
            await manager.broadcast_location_to_riders(ride_id, payload)
            
    except WebSocketDisconnect:
        manager.disconnect_driver(ride_id)
        await manager.send_alert_to_ride(ride_id, {
            "type": "safety_alert",
            "alert_type": "driver_disconnected",
            "message": "Driver tracking disconnected",
        })
    except Exception as e:
        logger.error(f"Driver WS error: {e}")
        manager.disconnect_driver(ride_id)


async def _handle_rider_ws(websocket: WebSocket, ride_id: str, user_id: str):
    """Rider receives location updates from driver."""
    await manager.connect_rider(ride_id, user_id, websocket)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to live tracking",
            "ride_id": ride_id,
        })
        
        # Keep connection open and handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                # Riders can send ping/heartbeat
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                break
            except Exception:
                break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Rider WS error: {e}")
    finally:
        manager.disconnect_rider(ride_id, user_id)
