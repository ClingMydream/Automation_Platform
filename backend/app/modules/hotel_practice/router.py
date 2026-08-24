import httpx

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import require_menu
from app.core.config import get_settings
from app.db import get_db
from app.models.entities import HotelBooking, HotelRoom
from app.modules.hotel_practice.schemas import BookingInput, RoomStatusInput


router = APIRouter(prefix="/v1/hotel-practice", tags=["hotel-practice"], dependencies=[Depends(require_menu("restful_booker"))])

INITIAL_ROOMS = [
    {"number": "101", "room_type": "标准大床房", "price": 399, "status": "可预订"},
    {"number": "202", "room_type": "舒适双床房", "price": 459, "status": "可预订"},
    {"number": "303", "room_type": "景观家庭房", "price": 599, "status": "维护中"},
]


def output(item):
    return {column.name: getattr(item, column.name) for column in item.__table__.columns}


def ensure_rooms(db: Session):
    if db.scalar(select(HotelRoom.id).limit(1)) is None:
        db.add_all(HotelRoom(**room) for room in INITIAL_ROOMS)
        db.commit()


@router.get("/rooms")
def list_rooms(db: Session = Depends(get_db)):
    ensure_rooms(db)
    return [output(room) for room in db.scalars(select(HotelRoom).order_by(HotelRoom.number)).all()]


@router.put("/rooms/{room_id}/status")
def update_room_status(room_id: int, payload: RoomStatusInput, db: Session = Depends(get_db)):
    ensure_rooms(db)
    room = db.get(HotelRoom, room_id)
    if not room:
        raise HTTPException(404, "房间不存在")
    room.status = payload.status
    db.commit()
    db.refresh(room)
    return output(room)


@router.get("/bookings")
def list_bookings(db: Session = Depends(get_db)):
    ensure_rooms(db)
    return [output(booking) for booking in db.scalars(select(HotelBooking).order_by(HotelBooking.created_at.desc())).all()]


@router.post("/bookings", status_code=201)
def create_booking(payload: BookingInput, db: Session = Depends(get_db)):
    ensure_rooms(db)
    if payload.checkout <= payload.checkin:
        raise HTTPException(400, "离店日期必须晚于入住日期")
    room = db.get(HotelRoom, payload.room_id)
    if not room:
        raise HTTPException(404, "房间不存在")
    if room.status != "可预订":
        raise HTTPException(409, "该房间当前不可预订")
    booking = HotelBooking(**payload.model_dump(), room_number=room.number)
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return output(booking)


@router.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.get(HotelBooking, booking_id)
    if not booking:
        raise HTTPException(404, "预约不存在")
    db.delete(booking)
    db.commit()
    return {"ok": True}


@router.delete("/booker-bookings/{booking_id}")
def cancel_booker_booking(booking_id: int):
    """Cancel a Restful Booker booking without exposing service credentials to the browser."""
    settings = get_settings()
    try:
        response = httpx.delete(
            f"{settings.restful_booker_url.rstrip('/')}/booking/{booking_id}",
            auth=(settings.restful_booker_username, settings.restful_booker_password),
            timeout=10,
        )
    except httpx.RequestError as error:
        raise HTTPException(502, "预约服务暂时无法连接") from error
    if response.status_code == 404:
        raise HTTPException(404, "预约不存在或已取消")
    if response.status_code not in (200, 201, 204):
        raise HTTPException(502, f"预约服务取消失败（HTTP {response.status_code}）")
    return {"ok": True, "booking_id": booking_id}
