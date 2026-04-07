from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from models.database import get_db
from models.models import User, Ride, SOSAlert
from models.schemas import SOSRequest, SOSResponse
from utils.auth import get_current_user
from websocket.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/safety", tags=["Safety"])


@router.post("/sos", response_model=SOSResponse)
async def trigger_sos(
    payload: SOSRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger SOS alert:
    1. Record alert in DB
    2. Notify trusted contacts (log/email simulation)
    3. Broadcast via WebSocket to ride participants
    4. Return Google Maps link
    """
    maps_link = None
    if payload.lat and payload.lng:
        maps_link = f"https://maps.google.com/?q={payload.lat},{payload.lng}"

    contacts = current_user.trusted_contacts or []
    notified = []
    
    # In production: send SMS/email to each contact
    for contact in contacts:
        logger.warning(
            f"SOS ALERT from {current_user.name} ({current_user.phone}): "
            f"Notifying {contact.get('name')} at {contact.get('phone')} | "
            f"Location: {maps_link or 'Unknown'} | "
            f"Message: {payload.message}"
        )
        notified.append(contact.get("name", "Unknown"))

    # Save to DB
    alert = SOSAlert(
        user_id=current_user.id,
        ride_id=payload.ride_id,
        lat=payload.lat,
        lng=payload.lng,
        message=payload.message,
        contacts_notified=contacts,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    # Broadcast via WebSocket if ride is active
    if payload.ride_id:
        await manager.send_alert_to_ride(payload.ride_id, {
            "type": "safety_alert",
            "alert_type": "sos",
            "message": f"🚨 SOS ALERT from {current_user.name}! Emergency assistance needed.",
            "user_id": current_user.id,
            "user_name": current_user.name,
            "lat": payload.lat,
            "lng": payload.lng,
            "maps_link": maps_link,
        })

    return SOSResponse(
        alert_id=alert.id,
        message=f"SOS alert sent to {len(notified)} contact(s): {', '.join(notified) or 'None'}",
        contacts_notified=len(notified),
        maps_link=maps_link,
    )


@router.get("/trip-share/{ride_id}")
async def get_trip_share_link(
    ride_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a shareable live tracking link for a ride."""
    result = await db.execute(select(Ride).where(Ride.id == ride_id))
    ride = result.scalar_one_or_none()
    if not ride:
        raise HTTPException(404, "Ride not found")
    
    from backend.utils.config import settings
    share_link = f"{settings.BACKEND_URL}/tracking?ride_id={ride_id}"
    
    return {
        "ride_id": ride_id,
        "share_link": share_link,
        "message": "Share this link with trusted contacts to let them track your trip",
        "expires": "When ride completes",
    }


@router.get("/alerts/{ride_id}")
async def get_ride_alerts(
    ride_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent safety alerts for a ride."""
    result = await db.execute(
        select(SOSAlert)
        .where(SOSAlert.ride_id == ride_id)
        .order_by(SOSAlert.created_at.desc())
        .limit(20)
    )
    alerts = result.scalars().all()
    return [
        {
            "id": a.id,
            "message": a.message,
            "lat": a.lat,
            "lng": a.lng,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]


@router.put("/trusted-contacts")
async def update_trusted_contacts(
    contacts: list,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update trusted contacts for SOS alerts."""
    current_user.trusted_contacts = contacts
    await db.commit()
    return {"message": f"Updated {len(contacts)} trusted contact(s)"}
