"""Synthetic test-data generators with explicit safety boundaries."""

from __future__ import annotations

import random
import re
from datetime import date, timedelta

from fastapi import HTTPException


ID_AREAS = ("110101", "310101", "440103", "440106", "510104", "330106")
ID_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
ID_CHECK_CODES = "10X98765432"
CN_MOBILE_PREFIXES = (
    "130", "131", "132", "133", "135", "136", "137", "138", "139",
    "150", "151", "152", "155", "156", "157", "158", "159",
    "170", "171", "172", "173", "175", "176", "177", "178",
    "180", "181", "182", "183", "185", "186", "187", "188", "189",
    "191", "193", "195", "196", "197", "198", "199",
)
TWILIO_MAGIC_NUMBER = "+15005550006"
E164_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


def id_checksum(body: str) -> str:
    """Return the PRC resident-ID checksum for a 17-digit body."""
    if len(body) != 17 or not body.isdigit():
        raise ValueError("ID body must contain exactly 17 digits")
    return ID_CHECK_CODES[sum(int(value) * weight for value, weight in zip(body, ID_WEIGHTS)) % 11]


def _random_birthday(rng: random.Random, min_year: int, max_year: int) -> date:
    start = date(min_year, 1, 1)
    end = date(max_year, 12, 31)
    return start + timedelta(days=rng.randint(0, (end - start).days))


def generate_id_cards(
    count: int,
    *,
    gender: str = "any",
    min_birth_year: int = 1970,
    max_birth_year: int = 2005,
    rng: random.Random | None = None,
) -> list[dict[str, object]]:
    """Generate checksum-valid synthetic PRC resident IDs for validation tests."""
    if min_birth_year > max_birth_year:
        raise HTTPException(status_code=422, detail="min_birth_year must not exceed max_birth_year")
    rng = rng or random.SystemRandom()
    results: list[dict[str, object]] = []
    seen: set[str] = set()
    while len(results) < count:
        birthday = _random_birthday(rng, min_birth_year, max_birth_year)
        sequence = rng.randint(1, 999)
        if gender == "male" and sequence % 2 == 0:
            sequence = sequence + 1 if sequence < 999 else 997
        elif gender == "female" and sequence % 2 == 1:
            sequence = sequence + 1 if sequence < 999 else 998
        body = f"{rng.choice(ID_AREAS)}{birthday:%Y%m%d}{sequence:03d}"
        value = body + id_checksum(body)
        if value in seen:
            continue
        seen.add(value)
        results.append(
            {
                "id_card": value,
                "birth_date": birthday.isoformat(),
                "gender": "male" if sequence % 2 else "female",
                "synthetic": True,
            }
        )
    return results


def configured_sms_numbers(raw_numbers: str | None) -> list[str]:
    """Parse and validate comma-separated, user-controlled E.164 receivers."""
    numbers = [item.strip() for item in (raw_numbers or "").split(",") if item.strip()]
    invalid = [item for item in numbers if not E164_PATTERN.fullmatch(item)]
    if invalid:
        raise HTTPException(status_code=500, detail="TEST_SMS_PHONE_NUMBERS contains an invalid E.164 number")
    return list(dict.fromkeys(numbers))


def generate_phone_numbers(
    count: int,
    *,
    mode: str,
    configured_numbers: str | None = None,
    rng: random.Random | None = None,
) -> list[dict[str, object]]:
    """Generate format-only numbers, a provider simulator, or controlled receivers."""
    rng = rng or random.SystemRandom()
    if mode == "configured_receivers":
        numbers = configured_sms_numbers(configured_numbers)
        if not numbers:
            raise HTTPException(
                status_code=409,
                detail="No controlled receivers configured; set TEST_SMS_PHONE_NUMBERS to owned E.164 numbers",
            )
        return [
            {
                "phone": numbers[index % len(numbers)],
                "sms_capable": True,
                "source": "configured_receiver",
                "synthetic": False,
            }
            for index in range(count)
        ]
    if mode == "twilio_magic":
        return [
            {
                "phone": TWILIO_MAGIC_NUMBER,
                "sms_capable": False,
                "source": "twilio_test_credentials",
                "synthetic": True,
                "note": "仅模拟供应商 API 校验，不会产生真实短信。",
            }
            for _ in range(count)
        ]
    seen: set[str] = set()
    while len(seen) < count:
        seen.add(f"{rng.choice(CN_MOBILE_PREFIXES)}{rng.randint(0, 99_999_999):08d}")
    return [
        {
            "phone": number,
            "sms_capable": False,
            "source": "cn_format_only",
            "synthetic": True,
            "note": "仅用于格式测试，禁止拨打或发送短信。",
        }
        for number in seen
    ]
