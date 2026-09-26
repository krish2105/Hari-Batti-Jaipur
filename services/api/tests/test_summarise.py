"""summarise(): flow-weighted averages, and the worst hour (busiest one when health ties)."""

from app.routers.junctions import summarise


def row(hour, health, flow):
    return {
        "hour": hour, "health": health, "flow_pcu_h": flow, "red_wait_s": 10.0, "cycles_to_clear": 1.0,
        "starvation": 1.0, "ped_ratio": 1.0, "spill_min": 0.0,
    }  # fmt: skip


def test_worst_hour_is_the_lowest_health():
    assert summarise([row(8, 90, 100), row(9, 70, 50), row(18, 80, 900)])["worstHour"] == 9


def test_a_health_tie_picks_the_busiest_hour_not_midnight():
    assert summarise([row(0, 85, 300), row(18, 85, 6000), row(3, 85, 200)])["worstHour"] == 18


def test_health_is_flow_weighted():
    assert summarise([row(8, 100, 100), row(9, 50, 300)])["health"] == 62.5
