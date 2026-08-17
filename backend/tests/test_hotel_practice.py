from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.modules.hotel_practice.router import cancel_booker_booking, cancel_booking, create_booking, list_bookings, list_rooms, update_room_status
from app.modules.hotel_practice.schemas import BookingInput, RoomStatusInput


def test_hotel_booking_api_flow(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'hotel.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        rooms = list_rooms(db)
        assert len(rooms) == 3
        booking = create_booking(BookingInput(room_id=rooms[0]["id"], guest="测试用户", phone="13800000000", checkin=date(2026, 8, 12), checkout=date(2026, 8, 13)), db)
        assert booking["room_number"] == "101"
        assert len(list_bookings(db)) == 1
        updated = update_room_status(rooms[0]["id"], RoomStatusInput(status="维护中"), db)
        assert updated["status"] == "维护中"
        assert cancel_booking(booking["id"], db) == {"ok": True}
        assert list_bookings(db) == []


def test_cancel_booker_booking_uses_server_side_auth(monkeypatch):
    captured = {}

    class Response:
        status_code = 201

    def fake_delete(url, auth, timeout):
        captured.update(url=url, auth=auth, timeout=timeout)
        return Response()

    monkeypatch.setattr("app.modules.hotel_practice.router.httpx.delete", fake_delete)
    result = cancel_booker_booking(2)

    assert result == {"ok": True, "booking_id": 2}
    assert captured["url"].endswith("/booking/2")
    assert captured["auth"] == ("admin", "password123")
