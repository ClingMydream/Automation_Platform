"""Request and response schemas for generated utility data."""

from typing import Any, Literal

from pydantic import BaseModel, Field


GeneratorKind = Literal["phone", "id_card"]
PhoneMode = Literal["cn_format", "twilio_magic", "configured_receivers"]
Gender = Literal["any", "male", "female"]


class DataGenerateRequest(BaseModel):
    """Options for generating non-production utility data."""

    kind: GeneratorKind
    count: int = Field(default=1, ge=1, le=100)
    phone_mode: PhoneMode = "cn_format"
    gender: Gender = "any"
    min_birth_year: int = Field(default=1970, ge=1900, le=2099)
    max_birth_year: int = Field(default=2005, ge=1900, le=2099)


class DataGenerateResponse(BaseModel):
    """Generated rows plus an explicit capability warning."""

    rows: list[dict[str, Any]]
    warning: str
