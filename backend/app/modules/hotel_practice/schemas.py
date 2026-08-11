from datetime import date

from pydantic import BaseModel, Field


class BookingInput(BaseModel):
    room_id: int
    guest: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=40)
    checkin: date
    checkout: date


class RoomStatusInput(BaseModel):
    status: str = Field(pattern="^(可预订|维护中)$")
