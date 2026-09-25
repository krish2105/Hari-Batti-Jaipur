"""GEH maths, pass/fail rule and the report header (no simulation needed)."""

import math

import pytest

from sim.calibrate import geh, report_header, share_ok, verdict


def test_geh_hand_example():
    assert geh(100, 120) == pytest.approx(1.907, abs=1e-3)  # sqrt(2*400/220)
    assert geh(0, 0) == 0.0
    assert geh(400, 300) == pytest.approx(math.sqrt(2 * 100**2 / 700))


def test_85_percent_rule():
    ok = [1.0] * 85 + [9.0] * 15
    assert share_ok(ok) == pytest.approx(0.85)
    assert verdict(share_ok(ok)) == "PASS"
    assert verdict(share_ok([1.0] * 84 + [9.0] * 16)) == "FAIL"
    assert verdict(float("nan")) == "no data"


def test_report_header_shows_schematic_label():
    manifest = {
        "geometry_label": "Schematic network – coordinates pending",
        "plans": {"demand2": {"J03": {"timing": "ASSUMED"}}},
    }
    head = "\n".join(report_header(manifest, "demand2", 24, 600))
    assert "Schematic network – coordinates pending" in head
    assert "Assumed timing – demand-proportional (2-phase, free left)" in head
    assert "ASSUMED" in head
