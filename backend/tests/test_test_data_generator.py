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


@pytest.mark.parametrize("mode", ["synthetic", "cn_format", "twilio_magic", "configured_receivers"])
def test_all_phone_modes_match_mobile_regex_and_warn_allocation_unknown(mode):
    rows = generate_phone_numbers(100, mode=mode, configured_numbers="+8613800138000")
    assert len({r["phone"] for r in rows}) == 100
    assert all(re.fullmatch(r"1[3-9][0-9]{9}", r["phone"]) for r in rows)
    assert all(r["sms_capable"] is False for r in rows)

    assert all(r["allocation_status"] == "unknown" and r["potentially_real"] for r in rows)
