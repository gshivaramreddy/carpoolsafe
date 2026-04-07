"""
Full Payment System
- Cost splitting: equal, by distance, by seats, custom
- Payment initiation and status tracking
- UPI deep-link generation
- Refund handling
- Ride-level payment summary
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid

from models.database import get_db
from models.models import (
    Payment, CostSplit, Booking, Ride, User,
    PaymentStatus, SplitMethod, BookingStatus
)
from utils.auth import get_current_user
from utils.geo import haversine_distance

router = APIRouter(prefix="/payment", tags=["Payments"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class InitiatePaymentRequest(BaseModel):
    booking_id: str
    payment_method: str  # upi, card, cash, wallet

class MarkPaidRequest(BaseModel):
    payment_id: str
    transaction_id: Optional[str] = None

class CustomSplitEntry(BaseModel):
    user_id: str
    amount: float

class ComputeSplitRequest(BaseModel):
    ride_id: str
    split_method: SplitMethod = SplitMethod.equal
    custom_splits: Optional[List[CustomSplitEntry]] = None


# ── Cost Split Engine ─────────────────────────────────────────────────────────

def compute_equal_split(total: float, bookings: list) -> dict:
    """Divide total equally among all riders."""
    n = len(bookings)
    if n == 0: return {}
    share = round(total / n, 2)
    return {b.rider_id: share for b in bookings}


def compute_distance_split(total: float, bookings: list) -> dict:
    """Split proportional to each rider's journey distance."""
    distances = {}
    for b in bookings:
        d = haversine_distance(b.pickup_lat, b.pickup_lng, b.drop_lat, b.drop_lng)
        distances[b.rider_id] = max(d, 0.1)
    total_dist = sum(distances.values())
    if total_dist == 0: return compute_equal_split(total, bookings)
    return {uid: round((d / total_dist) * total, 2) for uid, d in distances.items()}


def compute_seats_split(total: float, bookings: list) -> dict:
    """Split proportional to seats booked."""
    total_seats = sum(b.seats_booked for b in bookings)
    if total_seats == 0: return compute_equal_split(total, bookings)
    return {b.rider_id: round((b.seats_booked / total_seats) * total, 2) for b in bookings}


def generate_upi_link(amount: float, payee_upi: str, payee_name: str, note: str) -> str:
    """Generate a UPI deep link for payment."""
    note_enc = note.replace(" ", "%20")
    return f"upi://pay?pa={payee_upi}&pn={payee_name}&am={amount:.2f}&tn={note_enc}&cu=INR"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/split/compute")
async def compute_cost_split(
    payload: ComputeSplitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Compute cost split for a ride among all confirmed riders.
    Returns per-person amounts using the chosen split method.
    """
    # Load ride
    ride_result = await db.execute(select(Ride).where(Ride.id == payload.ride_id))
    ride = ride_result.scalar_one_or_none()
    if not ride: raise HTTPException(404, "Ride not found")
    if ride.driver_id != current_user.id:
        raise HTTPException(403, "Only the driver can compute splits")

    # Load all confirmed bookings for this ride
    bookings_result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.rider))
        .where(Booking.ride_id == payload.ride_id, Booking.status == BookingStatus.confirmed)
    )
    bookings = bookings_result.scalars().all()
    if not bookings:
        raise HTTPException(400, "No confirmed bookings for this ride")

    total = ride.estimated_price or sum(b.estimated_price or 0 for b in bookings)

    # Choose split method
    if payload.split_method == SplitMethod.equal:
        breakdown = compute_equal_split(total, bookings)
    elif payload.split_method == SplitMethod.distance:
        breakdown = compute_distance_split(total, bookings)
    elif payload.split_method == SplitMethod.seats:
        breakdown = compute_seats_split(total, bookings)
    elif payload.split_method == SplitMethod.custom:
        if not payload.custom_splits:
            raise HTTPException(400, "Custom splits required")
        breakdown = {e.user_id: e.amount for e in payload.custom_splits}
        if abs(sum(breakdown.values()) - total) > 1.0:
            raise HTTPException(400, f"Custom amounts must sum to ₹{total:.2f}")
    else:
        breakdown = compute_equal_split(total, bookings)

    # Upsert CostSplit record
    existing = await db.execute(select(CostSplit).where(CostSplit.ride_id == payload.ride_id))
    split_record = existing.scalar_one_or_none()
    if split_record:
        split_record.split_method = payload.split_method
        split_record.total_cost = total
        split_record.breakdown = breakdown
        split_record.updated_at = datetime.now(timezone.utc)
    else:
        split_record = CostSplit(
            ride_id=payload.ride_id, split_method=payload.split_method,
            total_cost=total, breakdown=breakdown,
        )
        db.add(split_record)
    await db.commit()

    # Build human-readable response
    rider_details = {b.rider_id: b.rider for b in bookings}
    return {
        "ride_id": payload.ride_id,
        "split_method": payload.split_method,
        "total_cost": round(total, 2),
        "per_person": [
            {
                "user_id": uid,
                "name": rider_details.get(uid).name if rider_details.get(uid) else "Unknown",
                "amount": amt,
                "seats": next((b.seats_booked for b in bookings if b.rider_id == uid), 1),
            }
            for uid, amt in breakdown.items()
        ],
        "split_id": split_record.id,
    }


@router.post("/initiate")
async def initiate_payment(
    payload: InitiatePaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Initiate a payment for a booking.
    For UPI: returns a deep link. For cash: marks as pending.
    """
    result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.ride).selectinload(Ride.driver))
        .where(Booking.id == payload.booking_id, Booking.rider_id == current_user.id)
    )
    booking = result.scalar_one_or_none()
    if not booking: raise HTTPException(404, "Booking not found")
    if booking.status != BookingStatus.confirmed:
        raise HTTPException(400, "Booking is not confirmed")

    # Check for existing pending payment
    existing = await db.execute(
        select(Payment).where(Payment.booking_id == payload.booking_id, Payment.payer_id == current_user.id, Payment.status == PaymentStatus.pending)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "Payment already initiated for this booking")

    amount = booking.estimated_price or 0
    driver = booking.ride.driver

    payment = Payment(
        booking_id=payload.booking_id,
        payer_id=current_user.id,
        payee_id=driver.id,
        amount=amount,
        payment_method=payload.payment_method,
        status=PaymentStatus.pending,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    response = {
        "payment_id": payment.id,
        "amount": amount,
        "currency": "INR",
        "payment_method": payload.payment_method,
        "status": "pending",
        "payee_name": driver.name,
    }

    # Generate UPI link if applicable
    if payload.payment_method == "upi":
        upi_id = f"{driver.phone or 'driver'}@upi"
        response["upi_link"] = generate_upi_link(
            amount, upi_id, driver.name, f"CarpoolSafe ride {booking.ride_id[:8]}"
        )
        response["upi_id"] = upi_id
        response["instruction"] = f"Pay ₹{amount:.2f} to {driver.name} via UPI"

    elif payload.payment_method == "cash":
        response["instruction"] = f"Pay ₹{amount:.2f} cash to the driver ({driver.name}) at drop-off"

    elif payload.payment_method == "wallet":
        response["instruction"] = f"₹{amount:.2f} will be deducted from your wallet"

    return response


@router.post("/confirm")
async def confirm_payment(
    payload: MarkPaidRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a payment as completed."""
    result = await db.execute(
        select(Payment).where(Payment.id == payload.payment_id, Payment.payer_id == current_user.id)
    )
    payment = result.scalar_one_or_none()
    if not payment: raise HTTPException(404, "Payment not found")
    if payment.status == PaymentStatus.completed:
        raise HTTPException(400, "Payment already completed")

    payment.status = PaymentStatus.completed
    payment.transaction_id = payload.transaction_id or f"TXN{uuid.uuid4().hex[:12].upper()}"
    payment.paid_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "payment_id": payment.id,
        "status": "completed",
        "amount": payment.amount,
        "transaction_id": payment.transaction_id,
        "paid_at": payment.paid_at.isoformat(),
    }


@router.post("/refund/{payment_id}")
async def refund_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Initiate refund for a completed payment (driver action)."""
    result = await db.execute(
        select(Payment).where(Payment.id == payment_id, Payment.payee_id == current_user.id)
    )
    payment = result.scalar_one_or_none()
    if not payment: raise HTTPException(404, "Payment not found or not yours")
    if payment.status != PaymentStatus.completed:
        raise HTTPException(400, "Only completed payments can be refunded")

    payment.status = PaymentStatus.refunded
    await db.commit()

    return {"payment_id": payment_id, "status": "refunded", "amount": payment.amount,
            "message": f"₹{payment.amount:.2f} refund initiated"}


@router.get("/ride/{ride_id}/summary")
async def get_ride_payment_summary(
    ride_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full payment summary for a ride — collections, splits, pending."""
    # Load bookings
    bookings_result = await db.execute(
        select(Booking)
        .options(selectinload(Booking.rider))
        .where(Booking.ride_id == ride_id, Booking.status == BookingStatus.confirmed)
    )
    bookings = bookings_result.scalars().all()

    # Load payments
    payments_result = await db.execute(
        select(Payment)
        .options(selectinload(Payment.payer))
        .where(Payment.booking_id.in_([b.id for b in bookings]))
    )
    payments = payments_result.scalars().all()

    # Load split record
    split_result = await db.execute(select(CostSplit).where(CostSplit.ride_id == ride_id))
    split = split_result.scalar_one_or_none()

    total_expected = sum(b.estimated_price or 0 for b in bookings)
    total_collected = sum(p.amount for p in payments if p.status == PaymentStatus.completed)
    total_pending = sum(p.amount for p in payments if p.status == PaymentStatus.pending)

    return {
        "ride_id": ride_id,
        "total_expected": round(total_expected, 2),
        "total_collected": round(total_collected, 2),
        "total_pending": round(total_pending, 2),
        "collection_rate": f"{(total_collected/total_expected*100):.0f}%" if total_expected else "0%",
        "split_method": split.split_method if split else None,
        "bookings": [{
            "booking_id": b.id, "rider": b.rider.name if b.rider else "?",
            "seats": b.seats_booked, "fare": b.estimated_price,
            "payment_status": next((p.status for p in payments if p.booking_id == b.id), "not_initiated"),
        } for b in bookings],
        "payments": [{
            "payment_id": p.id, "payer": p.payer.name if p.payer else "?",
            "amount": p.amount, "method": p.payment_method, "status": p.status,
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        } for p in payments],
    }


@router.get("/my-payments")
async def get_my_payments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all payments made by the current user."""
    result = await db.execute(
        select(Payment)
        .options(selectinload(Payment.payee))
        .where(Payment.payer_id == current_user.id)
        .order_by(Payment.created_at.desc())
    )
    payments = result.scalars().all()
    return [{
        "payment_id": p.id, "booking_id": p.booking_id,
        "payee": p.payee.name if p.payee else "?",
        "amount": p.amount, "currency": p.currency,
        "method": p.payment_method, "status": p.status,
        "transaction_id": p.transaction_id,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "paid_at": p.paid_at.isoformat() if p.paid_at else None,
    } for p in payments]
