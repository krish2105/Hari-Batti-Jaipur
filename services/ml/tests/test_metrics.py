"""The five Junction Health metrics and the Health Score, against hand-worked examples.

Common approach used below: 1 lane, sat 1800 PCU/h, g = 30 s, C = 60 s -> capacity = 900 PCU/h.
"""

import pytest

from ml.metrics import (
    ApproachHour,
    cycles_to_clear,
    degree_of_saturation,
    health_score,
    junction_metrics,
    ped_clearance_ratio,
    penalties,
    red_wait_s,
    spillback_minutes,
    starvation_ratio,
)


def ah(flow: float, **kw) -> ApproachHour:
    """Test approach: 1 lane, 30 s green of a 60 s cycle (capacity 900 PCU/h)."""
    return ApproachHour("J03", "A", 9, flow, 1, 30, 60, **kw)


def test_degree_of_saturation() -> None:
    # x = 720 / 900 = 0.8
    assert degree_of_saturation(ah(720)) == pytest.approx(0.8)


def test_red_wait() -> None:
    # d1 = 0.5*60*0.25 / (1 - 0.8*0.5) = 12.5
    # d2 = 225 * (-0.2 + sqrt(0.04 + 3.2/225)) = 225 * (-0.2 + 0.232857) = 7.393
    # red wait = 12.5 + 7.393 = 19.893 s
    assert red_wait_s(ah(720)) == pytest.approx(19.893, abs=1e-3)


def test_cycles_to_clear() -> None:
    # x = 0.8 -> max(1, 0.8) = 1.0; flow 1080 -> x = 1.2 -> 1.2
    assert cycles_to_clear(ah(720)) == 1.0
    assert cycles_to_clear(ah(1080)) == pytest.approx(1.2)


def test_starvation_ratio() -> None:
    # green needed = 720*60/(1800*1) / 0.9 = 24 / 0.9 = 26.667 s; ratio = 30 / 26.667 = 1.125
    assert starvation_ratio(ah(720)) == pytest.approx(1.125)
    # No flow -> capped at 10 (plenty of green), stays JSON-safe.
    assert starvation_ratio(ah(0)) == 10.0


def test_ped_clearance_ratio() -> None:
    # 15 s pedestrian green; 12 m crossing at 1.0 m/s needs 12 s -> 15/12 = 1.25
    assert ped_clearance_ratio(ah(720, crossing_width_m=12, ped_green_s=15)) == pytest.approx(1.25)
    assert ped_clearance_ratio(ah(720, crossing_width_m=12)) is None
    assert ped_clearance_ratio(ah(720)) is None


def test_spillback_below_capacity() -> None:
    # Red queue = 720*(60-30)/3600 = 6 PCU on 1 lane = 6*6.5 = 39 m.
    # Link 30 m -> spills every cycle -> 60 min; link 50 m -> 0 min; unknown link -> 0.
    assert spillback_minutes(ah(720, link_length_m=30)) == 60.0
    assert spillback_minutes(ah(720, link_length_m=50)) == 0.0
    assert spillback_minutes(ah(720)) == 0.0


def test_spillback_above_capacity() -> None:
    # flow 1080 > capacity 900. Red queue = 1080*30/3600 = 9 PCU.
    # Link 650 m holds 650/6.5 = 100 PCU. Growth = (1080-900)/60 = 3 PCU/min.
    # First passes the link at (100-9)/3 = 30.333 min -> spill = 60 - 30.333 = 29.667 min.
    assert spillback_minutes(ah(1080, link_length_m=650)) == pytest.approx(29.667, abs=1e-3)


def test_penalties_midpoints() -> None:
    # Each value sits halfway between good and bad -> every s = 0.5; Health = 100 - 100*0.5 = 50.
    m = {"red_wait_s": 45, "cycles_to_clear": 1.1, "starvation": 0.9, "ped_ratio": 1.1, "spill_min": 7.5}
    s = penalties(m)
    assert all(v == pytest.approx(0.5) for v in s.values())
    assert health_score(m) == 50.0


def test_penalties_ped_none() -> None:
    m = {"red_wait_s": 10, "cycles_to_clear": 1.0, "starvation": 1.5, "ped_ratio": None, "spill_min": 0}
    assert penalties(m)["s_ped"] is None


def test_health_all_zero_and_all_one() -> None:
    # All penalties 0 -> 100; all penalties 1 -> 100 - (30+25+20+15+10) = 0.
    zeros = {"s_wait": 0, "s_clear": 0, "s_starve": 0, "s_ped": 0, "s_spill": 0}
    ones = {"s_wait": 1, "s_clear": 1, "s_starve": 1, "s_ped": 1, "s_spill": 1}
    assert health_score(zeros) == 100.0
    assert health_score(ones) == 0.0
    # Same through the metrics path: all good -> 100, all bad -> 0.
    good = {"red_wait_s": 20, "cycles_to_clear": 1.0, "starvation": 1.1, "ped_ratio": 1.5, "spill_min": 0}
    bad = {"red_wait_s": 70, "cycles_to_clear": 1.5, "starvation": 0.5, "ped_ratio": 0.8, "spill_min": 20}
    assert health_score(good) == 100.0
    assert health_score(bad) == 0.0


def test_health_ped_none_rescales() -> None:
    # s_wait = 1, others 0, s_ped unknown: weights left = 30+25+20+10 = 85.
    # Health = 100 - 100*30/85 = 100 - 35.29 = 64.7
    s = {"s_wait": 1, "s_clear": 0, "s_starve": 0, "s_ped": None, "s_spill": 0}
    assert health_score(s) == 64.7


def test_junction_metrics_flow_weighted() -> None:
    # A: flow 720 (red wait 19.893, starvation 1.125). B: flow 360 -> x = 0.4:
    #   d1 = 7.5/(1-0.2) = 9.375; d2 = 225*(-0.6 + sqrt(0.36 + 1.6/225)) = 1.327 -> 10.702 s
    #   starvation = 30 / (360*60/1800/0.9) = 30/13.333 = 2.25
    # Weights 2/3 and 1/3: red wait = 2/3*19.893 + 1/3*10.702 = 16.829; starvation = 0.75 + 0.75 = 1.5
    # All penalties 0 and ped unknown -> Health 100.
    a = ah(720)
    b = ApproachHour("J03", "B", 9, 360, 1, 30, 60)
    out = junction_metrics([a, b])
    assert out["red_wait_s"] == pytest.approx(16.829, abs=1e-3)
    assert out["cycles_to_clear"] == 1.0
    assert out["starvation"] == pytest.approx(1.5)
    assert out["starvation_min"] == pytest.approx(1.125)
    assert out["ped_ratio"] is None
    assert out["spill_min"] == 0.0
    assert out["health"] == 100.0
    assert [m["approach"] for m in out["approaches"]] == ["A", "B"]


def test_junction_metrics_ped_min_and_spill_max() -> None:
    a = ah(720, crossing_width_m=12, ped_green_s=15, link_length_m=30)  # ped 1.25, spill 60
    b = ApproachHour("J03", "B", 9, 360, 1, 30, 60, crossing_width_m=10, ped_green_s=10)  # ped 1.0
    out = junction_metrics([a, b])
    assert out["ped_ratio"] == pytest.approx(1.0)
    assert out["spill_min"] == 60.0


def test_junction_metrics_empty() -> None:
    with pytest.raises(ValueError):
        junction_metrics([])
