"""
Advanced Ride Matching Engine
- Route-based matching (not just point-to-point)
- Haversine distance calculation
- Weighted scoring: pickup_dist, drop_dist, time_diff, price
- Direction validation
- Deviation rejection (>20%)
"""
from typing import List, Tuple
from datetime import datetime, timezone
import math

from backend.utils.geo import (
    haversine_distance,
    point_to_route_distance,
    validate_direction,
    is_point_between_on_route,
)
from backend.models.schemas import SearchRideRequest, RideMatchResult, RideResponse


# Matching weights (tunable)
W_PICKUP = 0.35    # pickup distance weight
W_DROP = 0.30      # drop distance weight
W_TIME = 0.20      # time difference weight
W_PRICE = 0.15     # price weight

MAX_PICKUP_DIST_KM = 5.0
MAX_DROP_DIST_KM = 5.0
MAX_TIME_DIFF_MINUTES = 60.0
MAX_DEVIATION_RATIO = 0.20  # Reject if detour adds >20% to driver route


def score_ride_match(
    pickup_dist: float,
    drop_dist: float,
    time_diff_minutes: float,
    price: float,
    max_price: float = 500.0,
) -> float:
    """
    Compute match score (lower = better match).
    Normalizes each factor to 0-1 range, then applies weights.
    """
    norm_pickup = min(pickup_dist / MAX_PICKUP_DIST_KM, 1.0)
    norm_drop = min(drop_dist / MAX_DROP_DIST_KM, 1.0)
    norm_time = min(abs(time_diff_minutes) / MAX_TIME_DIFF_MINUTES, 1.0)
    norm_price = min(price / max_price, 1.0) if max_price > 0 else 0.0

    score = (
        W_PICKUP * norm_pickup
        + W_DROP * norm_drop
        + W_TIME * norm_time
        + W_PRICE * norm_price
    )
    return round(score, 4)


def compute_match_metrics(
    ride,
    request: SearchRideRequest,
) -> Tuple[bool, float, float, float, float, float]:
    """
    Compute all matching metrics for a ride.
    Returns: (is_valid, pickup_dist, drop_dist, time_diff_min, price, score)
    """
    driver_src = (ride.source_lat, ride.source_lng)
    driver_dst = (ride.destination_lat, ride.destination_lng)
    rider_src = (request.pickup_lat, request.pickup_lng)
    rider_dst = (request.drop_lat, request.drop_lng)

    # 1. Direction validation
    if not validate_direction(driver_src, driver_dst, rider_src, rider_dst):
        return False, 0, 0, 0, 0, 0

    # 2. Calculate pickup distance (rider pickup to driver route)
    route_points = ride.route_points or []
    if route_points:
        pickup_dist = point_to_route_distance(rider_src, route_points)
    else:
        # Fallback: distance to driver's source
        pickup_dist = haversine_distance(*rider_src, *driver_src)

    if pickup_dist > request.max_pickup_distance_km:
        return False, pickup_dist, 0, 0, 0, 0

    # 3. Calculate drop distance (rider drop to driver route)
    if route_points:
        drop_dist = point_to_route_distance(rider_dst, route_points)
    else:
        drop_dist = haversine_distance(*rider_dst, *driver_dst)

    if drop_dist > request.max_drop_distance_km:
        return False, pickup_dist, drop_dist, 0, 0, 0

    # 4. Check that rider pickup is "before" drop on route (direction check)
    if not is_point_between_on_route(rider_src, driver_src, driver_dst):
        # Pickup is not on the driver's path
        if pickup_dist > 2.0:  # Allow some flexibility
            return False, pickup_dist, drop_dist, 0, 0, 0

    # 5. Route deviation check — does picking up rider add too much detour?
    driver_route_dist = haversine_distance(*driver_src, *driver_dst)
    if driver_route_dist > 0:
        detour = (pickup_dist + drop_dist) / driver_route_dist
        if detour > MAX_DEVIATION_RATIO:
            return False, pickup_dist, drop_dist, 0, 0, 0

    # 6. Time difference
    now = datetime.now(timezone.utc)
    ride_time = ride.departure_time
    if ride_time.tzinfo is None:
        from datetime import timezone as tz
        ride_time = ride_time.replace(tzinfo=tz.utc)

    if request.departure_time:
        req_time = request.departure_time
        if req_time.tzinfo is None:
            req_time = req_time.replace(tzinfo=timezone.utc)
        time_diff = abs((ride_time - req_time).total_seconds() / 60)
    else:
        time_diff = max(0, (ride_time - now).total_seconds() / 60)

    if time_diff > MAX_TIME_DIFF_MINUTES:
        return False, pickup_dist, drop_dist, time_diff, 0, 0

    # 7. Estimate price for rider's segment
    rider_distance = haversine_distance(*rider_src, *rider_dst)
    price = rider_distance * (ride.price_per_km or 2.0)

    # 8. Compute score
    all_prices = [500.0]  # default max; could be computed across all rides
    score = score_ride_match(pickup_dist, drop_dist, time_diff, price)

    return True, pickup_dist, drop_dist, time_diff, price, score


def rank_matches(
    results: List[RideMatchResult],
) -> List[RideMatchResult]:
    """Sort matches by score (ascending = best first)."""
    return sorted(results, key=lambda x: x.match_score)
