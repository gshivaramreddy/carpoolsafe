from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timezone
from typing import List, Optional

from models.database import get_db
from models.models import Ride, User, RideStatus
from models.schemas import (
    CreateRideRequest, RideResponse, SearchRideRequest, RideMatchResult
)
from utils.auth import get_current_user
from utils.geo import fetch_google_route, haversine_distance
from services.matching import compute_match_metrics, rank_matches
from services.ml_pricing import suggest_price, estimate_total_price

router = APIRouter(prefix="/ride", tags=["Rides"])


def _ride_to_response(ride: Ride) -> RideResponse:
    driver = ride.driver
    return RideResponse(
        id=ride.id,
        driver_id=ride.driver_id,
        driver_name=driver.name if driver else "Unknown",
        driver_gender=driver.gender if driver else None,
        driver_safety_score=driver.safety_score if driver else 5.0,
        vehicle_type=driver.vehicle_type if driver else None,
        source_address=ride.source_address,
        source_lat=ride.source_lat,
        source_lng=ride.source_lng,
        destination_address=ride.destination_address,
        destination_lat=ride.destination_lat,
        destination_lng=ride.destination_lng,
        departure_time=ride.departure_time,
        total_seats=ride.total_seats,
        available_seats=ride.available_seats,
        is_women_only=ride.is_women_only,
        price_per_km=ride.price_per_km,
        estimated_price=ride.estimated_price,
        total_distance_km=ride.total_distance_km,
        status=ride.status,
        route_polyline=ride.route_polyline,
        route_points=ride.route_points or [],
    )


@router.post("/create", response_model=RideResponse, status_code=201)
async def create_ride(
    payload: CreateRideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("driver", "both"):
        raise HTTPException(403, "Only drivers can create rides")

    # Fetch route from Google Maps
    polyline, route_points, distance_km = await fetch_google_route(
        payload.source_lat, payload.source_lng,
        payload.destination_lat, payload.destination_lng,
    )

    # Suggest price using ML service
    suggested_rate = suggest_price(
        distance_km or 0,
        payload.departure_time,
        payload.is_women_only,
    )
    price_per_km = payload.price_per_km or suggested_rate
    estimated_price = estimate_total_price(distance_km or 0, price_per_km)

    ride = Ride(
        driver_id=current_user.id,
        source_address=payload.source_address,
        source_lat=payload.source_lat,
        source_lng=payload.source_lng,
        destination_address=payload.destination_address,
        destination_lat=payload.destination_lat,
        destination_lng=payload.destination_lng,
        route_polyline=polyline,
        route_points=route_points or [],
        total_distance_km=distance_km,
        departure_time=payload.departure_time,
        total_seats=payload.total_seats,
        available_seats=payload.total_seats,
        is_women_only=payload.is_women_only,
        price_per_km=price_per_km,
        estimated_price=estimated_price,
    )
    db.add(ride)
    await db.commit()
    await db.refresh(ride)
    
    # Load driver relationship
    result = await db.execute(
        select(Ride).where(Ride.id == ride.id).join(User, Ride.driver_id == User.id)
    )
    # Attach driver manually
    ride.driver = current_user
    return _ride_to_response(ride)


@router.get("/my-rides", response_model=List[RideResponse])
async def get_my_rides(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Ride)
        .options(selectinload(Ride.driver))
        .where(Ride.driver_id == current_user.id)
        .order_by(Ride.departure_time.desc())
    )
    rides = result.scalars().all()
    return [_ride_to_response(r) for r in rides]


@router.get("/{ride_id}", response_model=RideResponse)
async def get_ride(
    ride_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Ride)
        .options(selectinload(Ride.driver))
        .where(Ride.id == ride_id)
    )
    ride = result.scalar_one_or_none()
    if not ride:
        raise HTTPException(404, "Ride not found")
    return _ride_to_response(ride)


@router.post("/search", response_model=List[RideMatchResult])
async def search_rides(
    payload: SearchRideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Advanced route-based ride matching engine.
    Filters and scores available rides by proximity, timing, and price.
    """
    from sqlalchemy.orm import selectinload
    
    # Women-only safety filter
    conditions = [
        Ride.available_seats >= payload.seats_needed,
        Ride.status == RideStatus.scheduled,
        Ride.departure_time > datetime.now(timezone.utc),
    ]
    
    if payload.women_only:
        conditions.append(Ride.is_women_only == True)
        if current_user.gender and current_user.gender.lower() != "female":
            raise HTTPException(403, "Women-only rides are restricted to female users")

    result = await db.execute(
        select(Ride)
        .options(selectinload(Ride.driver))
        .where(and_(*conditions))
        .order_by(Ride.departure_time)
        .limit(100)
    )
    rides = result.scalars().all()
    
    matches = []
    for ride in rides:
        is_valid, pickup_dist, drop_dist, time_diff, price, score = compute_match_metrics(
            ride, payload
        )
        if not is_valid:
            continue
        
        ride_resp = _ride_to_response(ride)
        matches.append(RideMatchResult(
            ride=ride_resp,
            match_score=score,
            pickup_distance_km=round(pickup_dist, 2),
            drop_distance_km=round(drop_dist, 2),
            time_diff_minutes=round(time_diff, 1),
            estimated_price=round(price, 2),
        ))
    
    return rank_matches(matches)[:20]  # Return top 20 matches
