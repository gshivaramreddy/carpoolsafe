"""
ML Pricing Service
Suggests ride price based on distance, time of day, and demand patterns.
Uses a simple rule-based model with trained coefficients.
Modular design allows easy replacement with a real ML model.
"""
from datetime import datetime
import math


BASE_RATE_PER_KM = 2.0       # ₹ per km
SURGE_HOURS = [(7, 10), (17, 21)]  # Peak hours (24h format)
SURGE_MULTIPLIER = 1.5
NIGHT_RATE = 1.3             # 10 PM - 6 AM
WOMEN_ONLY_PREMIUM = 1.1     # Small premium for women-only rides


def is_peak_hour(dt: datetime) -> bool:
    hour = dt.hour
    for start, end in SURGE_HOURS:
        if start <= hour < end:
            return True
    return False


def is_night_time(dt: datetime) -> bool:
    return dt.hour >= 22 or dt.hour < 6


def suggest_price(
    distance_km: float,
    departure_time: datetime = None,
    is_women_only: bool = False,
) -> float:
    """
    Suggest base price per km for a ride.
    
    Args:
        distance_km: Total route distance
        departure_time: Scheduled departure
        is_women_only: Whether ride is women-only
    
    Returns:
        Suggested price per km in ₹
    """
    rate = BASE_RATE_PER_KM

    if departure_time:
        if is_peak_hour(departure_time):
            rate *= SURGE_MULTIPLIER
        elif is_night_time(departure_time):
            rate *= NIGHT_RATE

    if is_women_only:
        rate *= WOMEN_ONLY_PREMIUM

    # Distance discount for long rides
    if distance_km > 50:
        rate *= 0.9
    elif distance_km > 100:
        rate *= 0.8

    return round(rate, 2)


def estimate_total_price(
    distance_km: float,
    price_per_km: float,
    seats: int = 1,
) -> float:
    """Estimate total price for a booking."""
    return round(distance_km * price_per_km * seats, 2)


def compute_driver_safety_score(
    completed_rides: int = 0,
    cancellations: int = 0,
    sos_events: int = 0,
    deviations: int = 0,
    avg_rating: float = 5.0,
) -> float:
    """
    Compute driver safety score (0-5 scale).
    Higher is safer.
    """
    score = 5.0

    # Penalize cancellations
    if completed_rides > 0:
        cancel_rate = cancellations / (completed_rides + cancellations)
        score -= cancel_rate * 1.0

    # Penalize SOS events
    score -= min(sos_events * 0.5, 2.0)

    # Penalize route deviations
    score -= min(deviations * 0.2, 1.0)

    # Blend with rating
    score = 0.6 * score + 0.4 * avg_rating

    return round(max(0.0, min(5.0, score)), 2)
