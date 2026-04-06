import math
from typing import List, Tuple, Optional
import httpx
from backend.utils.config import settings


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth.
    Returns distance in kilometers.
    """
    R = 6371  # Earth radius in km
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    
    a = (math.sin(dphi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def point_to_segment_distance(
    point: Tuple[float, float],
    seg_start: Tuple[float, float],
    seg_end: Tuple[float, float],
) -> float:
    """
    Minimum distance from a point to a line segment.
    All coordinates are (lat, lng). Returns km.
    """
    px, py = point
    ax, ay = seg_start
    bx, by = seg_end
    
    dx = bx - ax
    dy = by - ay
    
    if dx == 0 and dy == 0:
        return haversine_distance(px, py, ax, ay)
    
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    
    closest_x = ax + t * dx
    closest_y = ay + t * dy
    
    return haversine_distance(px, py, closest_x, closest_y)


def point_to_route_distance(
    point: Tuple[float, float],
    route_points: List[dict],
) -> float:
    """
    Minimum distance from a point to a polyline route.
    route_points: list of {lat, lng} dicts
    Returns distance in km.
    """
    if not route_points or len(route_points) < 2:
        if route_points:
            p = route_points[0]
            return haversine_distance(point[0], point[1], p["lat"], p["lng"])
        return float("inf")
    
    min_dist = float("inf")
    for i in range(len(route_points) - 1):
        seg_start = (route_points[i]["lat"], route_points[i]["lng"])
        seg_end = (route_points[i + 1]["lat"], route_points[i + 1]["lng"])
        dist = point_to_segment_distance(point, seg_start, seg_end)
        if dist < min_dist:
            min_dist = dist
    
    return min_dist


def validate_direction(
    driver_src: Tuple[float, float],
    driver_dst: Tuple[float, float],
    rider_src: Tuple[float, float],
    rider_dst: Tuple[float, float],
) -> bool:
    """
    Validate that the rider's journey is in the same general direction as the driver.
    Uses dot product of direction vectors.
    """
    driver_vec = (
        driver_dst[0] - driver_src[0],
        driver_dst[1] - driver_src[1],
    )
    rider_vec = (
        rider_dst[0] - rider_src[0],
        rider_dst[1] - rider_src[1],
    )
    
    dot = driver_vec[0] * rider_vec[0] + driver_vec[1] * rider_vec[1]
    return dot > 0


def is_point_between_on_route(
    point: Tuple[float, float],
    route_start: Tuple[float, float],
    route_end: Tuple[float, float],
) -> bool:
    """Check if a point lies roughly between start and end of route."""
    dist_start_to_point = haversine_distance(*route_start, *point)
    dist_point_to_end = haversine_distance(*point, *route_end)
    dist_start_to_end = haversine_distance(*route_start, *route_end)
    
    # Allow 20% tolerance
    return (dist_start_to_point + dist_point_to_end) <= dist_start_to_end * 1.20


def detect_route_deviation(
    current_lat: float,
    current_lng: float,
    route_points: List[dict],
    threshold_km: float = 0.5,
) -> Tuple[bool, float]:
    """
    Detect if current location deviates from planned route.
    Returns (is_deviated, deviation_distance_km)
    """
    if not route_points:
        return False, 0.0
    
    deviation = point_to_route_distance(
        (current_lat, current_lng), route_points
    )
    return deviation > threshold_km, deviation


async def fetch_google_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> Tuple[Optional[str], Optional[List[dict]], Optional[float]]:
    """
    Fetch route from Google Directions API.
    Returns (encoded_polyline, route_points_list, distance_km)
    """
    if not settings.GOOGLE_MAPS_API_KEY:
        # Return straight-line mock if no API key
        route_points = [
            {"lat": origin_lat, "lng": origin_lng},
            {"lat": dest_lat, "lng": dest_lng},
        ]
        distance = haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)
        return None, route_points, distance
    
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{origin_lat},{origin_lng}",
        "destination": f"{dest_lat},{dest_lng}",
        "key": settings.GOOGLE_MAPS_API_KEY,
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        data = resp.json()
    
    if data.get("status") != "OK":
        # Fallback to straight line
        route_points = [
            {"lat": origin_lat, "lng": origin_lng},
            {"lat": dest_lat, "lng": dest_lng},
        ]
        distance = haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)
        return None, route_points, distance
    
    route = data["routes"][0]
    leg = route["legs"][0]
    polyline = route["overview_polyline"]["encoded"]
    distance_km = leg["distance"]["value"] / 1000
    
    # Decode polyline steps into points
    route_points = []
    for step in leg["steps"]:
        start = step["start_location"]
        route_points.append({"lat": start["lat"], "lng": start["lng"]})
    end = leg["end_location"]
    route_points.append({"lat": end["lat"], "lng": end["lng"]})
    
    return polyline, route_points, distance_km


def decode_polyline(encoded: str) -> List[dict]:
    """Decode Google Maps encoded polyline to list of {lat, lng}."""
    points = []
    index = 0
    lat = 0
    lng = 0
    
    while index < len(encoded):
        b, shift, result = 0, 0, 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if result & 1 else result >> 1
        lat += dlat
        
        b, shift, result = 0, 0, 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if result & 1 else result >> 1
        lng += dlng
        
        points.append({"lat": lat / 1e5, "lng": lng / 1e5})
    
    return points
