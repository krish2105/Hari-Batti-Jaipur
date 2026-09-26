"""Schematic build (netconvert) and a short headless live run (uses the SUMO binaries)."""

import json

import pytest

from sim.clock import start_offset
from sim.config import GEOMETRY_LABELS
from sim.stream import ListPublisher, run

pytestmark = pytest.mark.sumo  # needs the SUMO binaries (netconvert, sumo)


def test_schematic_build_has_8_signals_and_flags(static_build):
    m = json.loads((static_build / "manifest.json").read_text(encoding="utf-8"))
    assert m["geometry"] == "SCHEMATIC"
    assert m["geometry_label"] == GEOMETRY_LABELS["SCHEMATIC"] == "Schematic network – coordinates pending"
    assert sorted(m["approaches"]) == [f"J0{i}" for i in range(1, 9)]
    for jid, apps in m["approaches"].items():
        assert len(apps) == 4, jid
        movements = {tuple(v) for v in m["links"][jid].values()}  # SUMO has one link per lane
        assert len(movements) == 12, jid  # all 12 surveyed turns exist
    assert any("coordinates pending" in f for f in m["flags"])
    assert any("Lanes assumed" in f for f in m["flags"])
    # J03 is the Sanganer Stadium end: its Metro-side arm is the link shared with J04
    assert m["approaches"]["J03"]["Mansarover Metro"]["in_edge"] == "J03_W_in"
    assert "M_J04_J03" in m["access"]


def test_all_three_plans_are_built(static_build):
    m = json.loads((static_build / "manifest.json").read_text(encoding="utf-8"))
    assert set(m["plans"]) == {"demand2", "webster4", "even"}
    assert m["plans"]["even"]["J05"]["cycle_s"] == 120
    for pid in m["plans"]:
        assert (static_build / f"tls_{pid}.add.xml").exists()
    y = m["webster_y"]["J01"]
    assert y["two_phase_y"] < y["approach_wise_y"]


def test_short_headless_run_publishes_32_states_per_second(static_build):
    pub = ListPublisher()
    run(static_build, start_offset("18:15"), "demand2", pub, ticks=120, realtime=False)
    assert len(pub.ticks) == 120
    for tick in pub.ticks:
        assert len(tick) == 32  # 8 junctions x 4 approaches
        assert {m["colour"] for m in tick} <= {"RED", "AMBER", "GREEN"}
        assert all(m["secondsRemaining"] >= 0 and m["source"] == "SIM" for m in tick)
    last = pub.ticks[-1]
    assert {m["junctionId"] for m in last} == {f"J0{i}" for i in range(1, 9)}
    assert all(m["timingLabel"].startswith("Assumed timing") for m in last)
    assert last[0]["simClock"].startswith("18:17:")
    # the countdown really counts down between ticks while the colour holds
    a, b = pub.ticks[10][0], pub.ticks[11][0]
    if a["colour"] == b["colour"]:
        assert b["secondsRemaining"] == a["secondsRemaining"] - 1
