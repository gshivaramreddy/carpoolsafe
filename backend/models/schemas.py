from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    driver = "driver"
    rider = "rider"
    both = "both"


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=2)
    phone: Optional[str] = None
    gender: Optional[str] = None
    role: UserRole = UserRole.rider
    vehicle_type: Optional[str] = None
    vehicle_number: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    role: str


# ── User ──────────────────────────────────────────────────────────────────────

class TrustedContact(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None


class UserProfile(BaseModel):
    id: str
    email: str
    name: str
    phone: Optional[str]
    gender: Optional[str]
    role: str
    vehicle_type: Optional[str]
    vehicle_number: Optional[str]
    trusted_contacts: List[dict] = []
    safety_score: float
    profile_picture: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_number: Optional[str] = None
    trusted_contacts: Optional[List[dict]] = None


# ── Rides ─────────────────────────────────────────────────────────────────────

class CreateRideRequest(BaseModel):
    source_address: str
    source_lat: float
    source_lng: float
    destination_address: str
    destination_lat: float
    destination_lng: float
    departure_time: datetime
    total_seats: int = Field(ge=1, le=8)
    is_women_only: bool = False
    price_per_km: float = Field(default=2.0, ge=0.5, le=20.0)


class RideResponse(BaseModel):
    id: str
    driver_id: str
    driver_name: str
    driver_gender: Optional[str]
    driver_safety_score: float
    vehicle_type: Optional[str]
    source_address: str
    source_lat: float
    source_lng: float
    destination_address: str
    destination_lat: float
    destination_lng: float
    departure_time: datetime
    total_seats: int
    available_seats: int
    is_women_only: bool
    price_per_km: float
    estimated_price: Optional[float]
    total_distance_km: Optional[float]
    status: str
    route_polyline: Optional[str]
    route_points: List[dict] = []

    class Config:
        from_attributes = True


# ── Search ────────────────────────────────────────────────────────────────────

class SearchRideRequest(BaseModel):
    pickup_lat: float
    pickup_lng: float
    pickup_address: str
    drop_lat: float
    drop_lng: float
    drop_address: str
    departure_time: Optional[datetime] = None
    seats_needed: int = 1
    women_only: bool = False
    max_pickup_distance_km: float = 3.0
    max_drop_distance_km: float = 3.0


class RideMatchResult(BaseModel):
    ride: RideResponse
    match_score: float
    pickup_distance_km: float
    drop_distance_km: float
    time_diff_minutes: float
    estimated_price: float


# ── Booking ───────────────────────────────────────────────────────────────────

class BookRideRequest(BaseModel):
    ride_id: str
    pickup_address: str
    pickup_lat: float
    pickup_lng: float
    drop_address: str
    drop_lat: float
    drop_lng: float
    seats_booked: int = 1


class BookingResponse(BaseModel):
    id: str
    ride_id: str
    rider_id: str
    pickup_address: str
    drop_address: str
    seats_booked: int
    estimated_price: Optional[float]
    status: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Safety ────────────────────────────────────────────────────────────────────

class SOSRequest(BaseModel):
    ride_id: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    message: Optional[str] = "EMERGENCY: I need help!"


class SOSResponse(BaseModel):
    alert_id: str
    message: str
    contacts_notified: int
    maps_link: Optional[str]


# ── Tracking ──────────────────────────────────────────────────────────────────

class LocationUpdate(BaseModel):
    ride_id: str
    lat: float
    lng: float
    speed: Optional[float] = None
    heading: Optional[float] = None
    timestamp: Optional[datetime] = None
