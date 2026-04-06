from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from typing import List

from backend.models.database import get_db
from backend.models.models import Ride, Booking, User, RideStatus, BookingStatus
from backend.models.schemas import BookRideRequest, BookingResponse
from backend.utils.auth import get_current_user
from backend.utils.geo import haversine_distance
from backend.services.ml_pricing import estimate_total_price

router = APIRouter(prefix="/booking", tags=["Bookings"])


@router.post("/book", response_model=BookingResponse, status_code=201)
async def book_ride(
    payload: BookRideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Book seats on a ride with optimistic locking to prevent overbooking.
    Uses SELECT FOR UPDATE to ensure atomicity.
    """
    # Check for existing booking
    existing = await db.execute(
        select(Booking).where(
            Booking.ride_id == payload.ride_id,
            Booking.rider_id == current_user.id,
            Booking.status == BookingStatus.confirmed,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "You already have a booking for this ride")

    # Fetch ride with row-level lock
    result = await db.execute(
        select(Ride)
        .options(selectinload(Ride.driver))
        .where(Ride.id == payload.ride_id)
        .with_for_update()
    )
    ride = result.scalar_one_or_none()
    
    if not ride:
        raise HTTPException(404, "Ride not found")
    if ride.status != RideStatus.scheduled:
        raise HTTPException(400, f"Ride is not available (status: {ride.status})")
    if ride.available_seats < payload.seats_booked:
        raise HTTPException(400, f"Only {ride.available_seats} seat(s) available")
    if ride.driver_id == current_user.id:
        raise HTTPException(400, "You cannot book your own ride")
    
    # Women-only check
    if ride.is_women_only:
        if not current_user.gender or current_user.gender.lower() != "female":
            raise HTTPException(403, "This is a women-only ride")

    # Calculate price
    dist = haversine_distance(
        payload.pickup_lat, payload.pickup_lng,
        payload.drop_lat, payload.drop_lng,
    )
    price = estimate_total_price(dist, ride.price_per_km, payload.seats_booked)

    # Create booking
    booking = Booking(
        ride_id=payload.ride_id,
        rider_id=current_user.id,
        pickup_address=payload.pickup_address,
        pickup_lat=payload.pickup_lat,
        pickup_lng=payload.pickup_lng,
        drop_address=payload.drop_address,
        drop_lat=payload.drop_lat,
        drop_lng=payload.drop_lng,
        seats_booked=payload.seats_booked,
        estimated_price=price,
        status=BookingStatus.confirmed,
    )
    db.add(booking)

    # Decrement available seats atomically
    ride.available_seats -= payload.seats_booked
    if ride.available_seats == 0:
        ride.status = RideStatus.active

    await db.commit()
    await db.refresh(booking)
    
    return booking


@router.get("/my-bookings", response_model=List[BookingResponse])
async def get_my_bookings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Booking)
        .where(Booking.rider_id == current_user.id)
        .order_by(Booking.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/cancel/{booking_id}")
async def cancel_booking(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Booking)
        .where(Booking.id == booking_id, Booking.rider_id == current_user.id)
        .with_for_update()
    )
    booking = result.scalar_one_or_none()
    
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.status == BookingStatus.cancelled:
        raise HTTPException(400, "Booking already cancelled")

    # Return seats
    ride_result = await db.execute(
        select(Ride).where(Ride.id == booking.ride_id).with_for_update()
    )
    ride = ride_result.scalar_one_or_none()
    if ride:
        ride.available_seats += booking.seats_booked
        if ride.status == RideStatus.active and ride.available_seats > 0:
            ride.status = RideStatus.scheduled

    booking.status = BookingStatus.cancelled
    await db.commit()
    
    return {"message": "Booking cancelled successfully"}
