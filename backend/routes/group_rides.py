"""
Group Ride Coordination API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from models.database import get_db
from models.models import (
    GroupRide, GroupMember, GroupMessage, GroupScheduleVote,
    GroupRideStatus, GroupMemberStatus, User, Ride
)
from backend.utils.auth import get_current_user

router = APIRouter(prefix="/group", tags=["Group Rides"])

class CreateGroupRequest(BaseModel):
    name: str
    description: Optional[str] = None
    destination_address: Optional[str] = None
    destination_lat: Optional[float] = None
    destination_lng: Optional[float] = None
    proposed_date: Optional[datetime] = None
    max_members: int = 8

class SetPickupRequest(BaseModel):
    pickup_address: str
    pickup_lat: float
    pickup_lng: float

class SendMessageRequest(BaseModel):
    content: str

class ProposeTimeRequest(BaseModel):
    proposed_time: datetime

class VoteTimeRequest(BaseModel):
    schedule_vote_id: str

class ConfirmGroupRequest(BaseModel):
    ride_id: str


def _serialize_member(m):
    return {
        "id": m.id, "group_id": m.group_id, "user_id": m.user_id,
        "user_name": m.user.name if m.user else "Unknown",
        "user_gender": m.user.gender if m.user else None,
        "status": m.status, "pickup_address": m.pickup_address,
        "pickup_lat": m.pickup_lat, "pickup_lng": m.pickup_lng,
        "joined_at": m.joined_at.isoformat() if m.joined_at else None,
    }

def _serialize_message(msg):
    return {
        "id": msg.id, "group_id": msg.group_id, "sender_id": msg.sender_id,
        "sender_name": msg.sender.name if msg.sender else "Unknown",
        "content": msg.content, "message_type": msg.message_type,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }

def _serialize_schedule(s):
    return {
        "id": s.id, "group_id": s.group_id, "proposed_by": s.user_id,
        "proposed_time": s.proposed_time.isoformat(),
        "votes": s.votes or [], "vote_count": len(s.votes or []),
    }


@router.post("/create", status_code=201)
async def create_group(payload: CreateGroupRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    group = GroupRide(
        name=payload.name, description=payload.description,
        organizer_id=current_user.id,
        destination_address=payload.destination_address,
        destination_lat=payload.destination_lat, destination_lng=payload.destination_lng,
        proposed_date=payload.proposed_date, max_members=payload.max_members,
    )
    db.add(group)
    await db.flush()
    db.add(GroupMember(group_id=group.id, user_id=current_user.id, status=GroupMemberStatus.accepted))
    db.add(GroupMessage(group_id=group.id, sender_id=current_user.id,
        content=f"{current_user.name} created the group. Invite code: {group.invite_code}", message_type="system"))
    await db.commit()
    await db.refresh(group)
    return {"id": group.id, "name": group.name, "invite_code": group.invite_code,
            "status": group.status, "message": f"Group created! Share code: {group.invite_code}"}


@router.post("/join/{invite_code}")
async def join_group(invite_code: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(GroupRide).options(selectinload(GroupRide.members)).where(GroupRide.invite_code == invite_code.upper()))
    group = result.scalar_one_or_none()
    if not group: raise HTTPException(404, "Invalid invite code")
    if group.status not in (GroupRideStatus.open, GroupRideStatus.locked): raise HTTPException(400, f"Group is {group.status}")
    if any(m.user_id == current_user.id for m in group.members): raise HTTPException(400, "Already a member")
    active = [m for m in group.members if m.status == GroupMemberStatus.accepted]
    if len(active) >= group.max_members: raise HTTPException(400, "Group is full")
    db.add(GroupMember(group_id=group.id, user_id=current_user.id, status=GroupMemberStatus.accepted))
    db.add(GroupMessage(group_id=group.id, sender_id=current_user.id, content=f"{current_user.name} joined the group.", message_type="system"))
    await db.commit()
    return {"message": f"Joined '{group.name}' successfully!", "group_id": group.id}


@router.get("/my-groups")
async def get_my_groups(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(GroupMember)
        .options(selectinload(GroupMember.group).selectinload(GroupRide.organizer),
                 selectinload(GroupMember.group).selectinload(GroupRide.members))
        .where(GroupMember.user_id == current_user.id, GroupMember.status == GroupMemberStatus.accepted)
    )
    memberships = result.scalars().all()
    return [{
        "group_id": m.group.id, "name": m.group.name, "invite_code": m.group.invite_code,
        "status": m.group.status, "organizer": m.group.organizer.name if m.group.organizer else "?",
        "member_count": len([x for x in m.group.members if x.status == GroupMemberStatus.accepted]),
        "destination": m.group.destination_address,
        "proposed_date": m.group.proposed_date.isoformat() if m.group.proposed_date else None,
        "is_organizer": m.group.organizer_id == current_user.id,
    } for m in memberships]


@router.get("/{group_id}")
async def get_group_detail(group_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(
        select(GroupRide)
        .options(selectinload(GroupRide.organizer),
                 selectinload(GroupRide.members).selectinload(GroupMember.user),
                 selectinload(GroupRide.messages).selectinload(GroupMessage.sender),
                 selectinload(GroupRide.schedules))
        .where(GroupRide.id == group_id)
    )
    group = result.scalar_one_or_none()
    if not group: raise HTTPException(404, "Group not found")
    if not any(m.user_id == current_user.id and m.status == GroupMemberStatus.accepted for m in group.members):
        raise HTTPException(403, "Not a member")
    return {
        "id": group.id, "name": group.name, "description": group.description,
        "organizer_id": group.organizer_id, "organizer_name": group.organizer.name if group.organizer else "?",
        "destination_address": group.destination_address, "destination_lat": group.destination_lat,
        "destination_lng": group.destination_lng,
        "proposed_date": group.proposed_date.isoformat() if group.proposed_date else None,
        "max_members": group.max_members, "ride_id": group.ride_id, "status": group.status,
        "invite_code": group.invite_code,
        "members": [_serialize_member(m) for m in group.members if m.status == GroupMemberStatus.accepted],
        "messages": [_serialize_message(msg) for msg in sorted(group.messages, key=lambda x: x.created_at)],
        "schedules": [_serialize_schedule(s) for s in group.schedules],
        "created_at": group.created_at.isoformat() if group.created_at else None,
    }


@router.put("/{group_id}/pickup")
async def set_my_pickup(group_id: str, payload: SetPickupRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == current_user.id))
    member = result.scalar_one_or_none()
    if not member: raise HTTPException(404, "Not a member")
    member.pickup_address = payload.pickup_address
    member.pickup_lat = payload.pickup_lat
    member.pickup_lng = payload.pickup_lng
    await db.commit()
    return {"message": "Pickup location updated"}


@router.post("/{group_id}/message")
async def send_message(group_id: str, payload: SendMessageRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == current_user.id, GroupMember.status == GroupMemberStatus.accepted))
    if not result.scalar_one_or_none(): raise HTTPException(403, "Not a member")
    msg = GroupMessage(group_id=group_id, sender_id=current_user.id, content=payload.content, message_type="text")
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    msg.sender = current_user
    return _serialize_message(msg)


@router.post("/{group_id}/schedule/propose")
async def propose_time(group_id: str, payload: ProposeTimeRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == current_user.id))
    if not result.scalar_one_or_none(): raise HTTPException(403, "Not a member")
    slot = GroupScheduleVote(group_id=group_id, user_id=current_user.id, proposed_time=payload.proposed_time, votes=[current_user.id])
    db.add(slot)
    db.add(GroupMessage(group_id=group_id, sender_id=current_user.id,
        content=f"{current_user.name} proposed {payload.proposed_time.strftime('%d %b %Y %H:%M')} as departure time.", message_type="system"))
    await db.commit()
    await db.refresh(slot)
    return _serialize_schedule(slot)


@router.post("/{group_id}/schedule/vote")
async def vote_for_time(group_id: str, payload: VoteTimeRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(GroupScheduleVote).where(GroupScheduleVote.id == payload.schedule_vote_id, GroupScheduleVote.group_id == group_id))
    slot = result.scalar_one_or_none()
    if not slot: raise HTTPException(404, "Schedule slot not found")
    votes = list(slot.votes or [])
    if current_user.id in votes: votes.remove(current_user.id)
    else: votes.append(current_user.id)
    slot.votes = votes
    await db.commit()
    return {"schedule_vote_id": slot.id, "votes": votes, "vote_count": len(votes)}


@router.post("/{group_id}/confirm")
async def confirm_group_ride(group_id: str, payload: ConfirmGroupRequest, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(GroupRide).options(selectinload(GroupRide.members).selectinload(GroupMember.user)).where(GroupRide.id == group_id))
    group = result.scalar_one_or_none()
    if not group: raise HTTPException(404, "Group not found")
    if group.organizer_id != current_user.id: raise HTTPException(403, "Only organizer can confirm")
    ride_result = await db.execute(select(Ride).where(Ride.id == payload.ride_id))
    ride = ride_result.scalar_one_or_none()
    if not ride: raise HTTPException(404, "Ride not found")
    group.ride_id = payload.ride_id
    group.status = GroupRideStatus.confirmed
    db.add(GroupMessage(group_id=group_id, sender_id=current_user.id,
        content=f"Ride confirmed for {ride.departure_time.strftime('%d %b %Y %H:%M')}! Book your seats now.", message_type="system"))
    await db.commit()
    active = [m for m in group.members if m.status == GroupMemberStatus.accepted]
    return {"message": "Group ride confirmed!", "group_id": group_id, "ride_id": payload.ride_id,
            "member_count": len(active), "departure": ride.departure_time.isoformat()}


@router.delete("/{group_id}/leave")
async def leave_group(group_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == current_user.id))
    member = result.scalar_one_or_none()
    if not member: raise HTTPException(404, "Not in this group")
    group_result = await db.execute(select(GroupRide).where(GroupRide.id == group_id))
    group = group_result.scalar_one_or_none()
    if group and group.organizer_id == current_user.id: raise HTTPException(400, "Organizer cannot leave — cancel instead")
    member.status = GroupMemberStatus.declined
    db.add(GroupMessage(group_id=group_id, sender_id=current_user.id, content=f"{current_user.name} left the group.", message_type="system"))
    await db.commit()
    return {"message": "Left the group"}
