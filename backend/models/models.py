from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, 
    ForeignKey, Text, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func
import uuid
import enum


class Base(DeclarativeBase):
    pass


def generate_uuid():
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    driver = "driver"
    rider = "rider"
    both = "both"


class RideStatus(str, enum.Enum):
    scheduled = "scheduled"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class BookingStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)
    role = Column(SAEnum(UserRole), default=UserRole.rider)
    
    # Driver fields
    vehicle_type = Column(String, nullable=True)
    vehicle_number = Column(String, nullable=True)
    
    # Safety
    trusted_contacts = Column(JSON, default=list)
    safety_score = Column(Float, default=5.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    rides_as_driver = relationship("Ride", back_populates="driver", foreign_keys="Ride.driver_id")
    bookings = relationship("Booking", back_populates="rider", foreign_keys="Booking.rider_id")


class Ride(Base):
    __tablename__ = "rides"

    id = Column(String, primary_key=True, default=generate_uuid)
    driver_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Route
    source_address = Column(String, nullable=False)
    source_lat = Column(Float, nullable=False)
    source_lng = Column(Float, nullable=False)
    destination_address = Column(String, nullable=False)
    destination_lat = Column(Float, nullable=False)
    destination_lng = Column(Float, nullable=False)
    route_polyline = Column(Text, nullable=True)
    route_points = Column(JSON, default=list)  # List of {lat, lng} waypoints
    total_distance_km = Column(Float, nullable=True)
    
    # Schedule
    departure_time = Column(DateTime(timezone=True), nullable=False)
    
    # Capacity
    total_seats = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)
    
    # Safety
    is_women_only = Column(Boolean, default=False)
    
    # Pricing
    price_per_km = Column(Float, default=2.0)
    estimated_price = Column(Float, nullable=True)
    
    # Status
    status = Column(SAEnum(RideStatus), default=RideStatus.scheduled)
    
    # Live tracking
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    last_location_update = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    driver = relationship("User", back_populates="rides_as_driver", foreign_keys=[driver_id])
    bookings = relationship("Booking", back_populates="ride")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String, primary_key=True, default=generate_uuid)
    ride_id = Column(String, ForeignKey("rides.id"), nullable=False)
    rider_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Pickup/Drop
    pickup_address = Column(String, nullable=False)
    pickup_lat = Column(Float, nullable=False)
    pickup_lng = Column(Float, nullable=False)
    drop_address = Column(String, nullable=False)
    drop_lat = Column(Float, nullable=False)
    drop_lng = Column(Float, nullable=False)
    
    # Seats
    seats_booked = Column(Integer, default=1)
    
    # Pricing
    estimated_price = Column(Float, nullable=True)
    
    # Status
    status = Column(SAEnum(BookingStatus), default=BookingStatus.confirmed)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    ride = relationship("Ride", back_populates="bookings")
    rider = relationship("User", back_populates="bookings", foreign_keys=[rider_id])


class SOSAlert(Base):
    __tablename__ = "sos_alerts"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    ride_id = Column(String, ForeignKey("rides.id"), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    contacts_notified = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ── Group Ride Models ──────────────────────────────────────────────────────────

class GroupRideStatus(str, enum.Enum):
    open = "open"
    locked = "locked"
    confirmed = "confirmed"
    cancelled = "cancelled"

class GroupMemberStatus(str, enum.Enum):
    invited = "invited"
    accepted = "accepted"
    declined = "declined"
    removed = "removed"

class GroupRide(Base):
    __tablename__ = "group_rides"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    organizer_id = Column(String, ForeignKey("users.id"), nullable=False)
    destination_address = Column(String, nullable=True)
    destination_lat = Column(Float, nullable=True)
    destination_lng = Column(Float, nullable=True)
    proposed_date = Column(DateTime(timezone=True), nullable=True)
    max_members = Column(Integer, default=8)
    ride_id = Column(String, ForeignKey("rides.id"), nullable=True)
    status = Column(SAEnum(GroupRideStatus), default=GroupRideStatus.open)
    invite_code = Column(String, unique=True, nullable=False, default=lambda: str(uuid.uuid4())[:8].upper())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    organizer = relationship("User", foreign_keys=[organizer_id])
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    messages = relationship("GroupMessage", back_populates="group", cascade="all, delete-orphan")
    schedules = relationship("GroupScheduleVote", back_populates="group", cascade="all, delete-orphan")

class GroupMember(Base):
    __tablename__ = "group_members"
    id = Column(String, primary_key=True, default=generate_uuid)
    group_id = Column(String, ForeignKey("group_rides.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(SAEnum(GroupMemberStatus), default=GroupMemberStatus.accepted)
    pickup_address = Column(String, nullable=True)
    pickup_lat = Column(Float, nullable=True)
    pickup_lng = Column(Float, nullable=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    group = relationship("GroupRide", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])

class GroupMessage(Base):
    __tablename__ = "group_messages"
    id = Column(String, primary_key=True, default=generate_uuid)
    group_id = Column(String, ForeignKey("group_rides.id"), nullable=False)
    sender_id = Column(String, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String, default="text")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    group = relationship("GroupRide", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])

class GroupScheduleVote(Base):
    __tablename__ = "group_schedule_votes"
    id = Column(String, primary_key=True, default=generate_uuid)
    group_id = Column(String, ForeignKey("group_rides.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    proposed_time = Column(DateTime(timezone=True), nullable=False)
    votes = Column(JSON, default=list)
    group = relationship("GroupRide", back_populates="schedules")


# ── Payment Models ─────────────────────────────────────────────────────────────

class PaymentStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"

class SplitMethod(str, enum.Enum):
    equal = "equal"
    distance = "distance"
    seats = "seats"
    custom = "custom"

class Payment(Base):
    __tablename__ = "payments"
    id = Column(String, primary_key=True, default=generate_uuid)
    booking_id = Column(String, ForeignKey("bookings.id"), nullable=False)
    payer_id = Column(String, ForeignKey("users.id"), nullable=False)
    payee_id = Column(String, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    status = Column(SAEnum(PaymentStatus), default=PaymentStatus.pending)
    payment_method = Column(String, nullable=True)
    transaction_id = Column(String, nullable=True)
    gateway_response = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)
    booking = relationship("Booking", foreign_keys=[booking_id])
    payer = relationship("User", foreign_keys=[payer_id])
    payee = relationship("User", foreign_keys=[payee_id])

class CostSplit(Base):
    __tablename__ = "cost_splits"
    id = Column(String, primary_key=True, default=generate_uuid)
    ride_id = Column(String, ForeignKey("rides.id"), nullable=False)
    split_method = Column(SAEnum(SplitMethod), default=SplitMethod.equal)
    total_cost = Column(Float, nullable=False)
    breakdown = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    ride = relationship("Ride", foreign_keys=[ride_id])
