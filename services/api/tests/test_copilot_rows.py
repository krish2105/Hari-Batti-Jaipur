"""The copilot turns SQL result values into JSON: Postgres AVG()/SUM() give Decimal, dates give date."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal

from app.copilot.agent import _jsonable


def test_decimal_becomes_a_rounded_float():
    assert _jsonable(Decimal("12.3456")) == 12.35
    assert isinstance(_jsonable(Decimal(7)), float)


def test_dates_and_times_become_iso_strings():
    assert _jsonable(date(2026, 5, 11)) == "2026-05-11"
    assert _jsonable(datetime(2026, 5, 11, 18, 0, tzinfo=UTC)).startswith("2026-05-11T18:00")


def test_a_typical_row_is_json_serialisable():
    row = [_jsonable(v) for v in ("J05", Decimal("85.0"), 18, 1.23456, None, date(2026, 5, 12))]
    assert json.loads(json.dumps(row)) == ["J05", 85.0, 18, 1.23, None, "2026-05-12"]
