"""Tests for synthetic phone and resident-ID generators."""

import random
import re
from datetime import date

import pytest
from fastapi import HTTPException

from app.modules.data_generator.service import generate_id_cards, generate_phone_numbers, id_checksum


def test_id_cards_have_valid_checksum_birth_date_and_requested_gender():
    rows = generate_id_cards(20, gender="female", min_birth_year=1990, max_birth_year=1992, rng=random.Random(7))

    assert len(rows) == 20
    assert len({row["id_card"] for row in rows}) == 20
    for row in rows:
        value = row["id_card"]
        assert re.fullmatch(r"\d{17}[0-9X]", value)
        assert value[-1] == id_checksum(value[:17])
        assert date.fromisoformat(row["birth_date"])
        assert value[6:14] == row["birth_date"].replace("-", "")
        assert row["gender"] == "female"
        assert int(value[16]) % 2 == 0


def test_cn_format_phone_numbers_are_unique_and_not_marked_sms_capable():
    rows = generate_phone_numbers(30, mode="cn_format", rng=random.Random(11))

    assert len({row["phone"] for row in rows}) == 30
    assert all(re.fullmatch(r"1\d{10}", row["phone"]) for row in rows)
    assert all(row["sms_capable"] is False for row in rows)


def test_configured_receivers_only_return_controlled_e164_numbers():
    rows = generate_phone_numbers(3, mode="configured_receivers", configured_numbers="+14155550100, +442079460018")

    assert [row["phone"] for row in rows] == ["+14155550100", "+442079460018", "+14155550100"]
    assert all(row["sms_capable"] is True for row in rows)


def test_configured_receivers_fail_closed_when_not_configured():
    with pytest.raises(HTTPException) as exc_info:
        generate_phone_numbers(1, mode="configured_receivers", configured_numbers="")

    assert exc_info.value.status_code == 409
