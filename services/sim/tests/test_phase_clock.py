"""Countdown logic and the India-time clock (pure functions, no SUMO)."""

from datetime import UTC, datetime

from sim.clock import clock_to_sim_offset, parse_hhmm, sim_clock_label, start_offset
from sim.phase import (
    ApproachLinks,
    approach_colour,
    choose_report_links,
    seconds_until_change,
    to_phase_state,
)

# links 0,1 = W straight; 2 = N straight. Program: W green 20, amber 3, all-red 2, N green 30, amber 3, all-red 2
PROGRAM = [(20, "GGr"), (3, "yyr"), (2, "rrr"), (30, "rrG"), (3, "rry"), (2, "rrr")]


def test_colour_mapping():
    assert approach_colour("GGr", (0, 1)) == "GREEN"
    assert approach_colour("ggr", (0, 1)) == "GREEN"
    assert approach_colour("yyr", (0, 1)) == "AMBER"
    assert approach_colour("rrG", (0, 1)) == "RED"


def test_seconds_until_change_walks_the_program():
    assert seconds_until_change(PROGRAM, 0, 12, (0, 1)) == 12  # green -> amber in 12 s
    assert seconds_until_change(PROGRAM, 2, 1, (0, 1)) == 1 + 30 + 3 + 2  # red lasts all-red + N phase
    # wraps across the end of the cycle: N is red from phase 4's end through W's phases
    assert seconds_until_change(PROGRAM, 5, 2, (2,)) == 2 + 20 + 3 + 2


def test_always_green_returns_cycle():
    assert seconds_until_change([(10, "G"), (5, "G")], 0, 4, (0,)) == 15


def test_report_links_prefer_straight():
    links = {0: ("W", "L"), 1: ("W", "S"), 2: ("W", "S"), 3: ("W", "R"), 4: ("N", "R")}
    assert choose_report_links(links, "W") == (1, 2)
    assert choose_report_links(links, "N") == (4,)


def test_phase_state_shape():
    ap = ApproachLinks("J04", "J04-durgapur", "Durgapur", (2,))
    msg = to_phase_state(
        ap,
        "RED",
        17.4,
        datetime(2026, 9, 26, 12, 0, tzinfo=UTC),
        confidence=0.9,
        timing="ASSUMED",
        timing_label="Assumed timing – demand-proportional (2-phase, free left)",
        geometry="SCHEMATIC",
        geometry_label="Schematic network – coordinates pending",
        sim_clock="18:15:00 IST, survey day 2026-05-11",
    )
    core_keys = {
        "junctionId",
        "approachId",
        "colour",
        "secondsRemaining",
        "confidence",
        "source",
        "updatedAt",
    }
    assert core_keys <= set(msg)
    assert msg["source"] == "SIM" and msg["confidence"] == 0.9 and msg["secondsRemaining"] == 17
    assert msg["timingLabel"].startswith("Assumed timing")
    assert msg["geometryLabel"] == "Schematic network – coordinates pending"


def test_clock_uses_india_time_not_the_mac():
    # 22:00 in Dubai (UTC+4) = 18:00 UTC = 23:30 IST -> 15.5 h after the 08:00 survey start
    dubai_22 = datetime(2026, 9, 25, 18, 0, tzinfo=UTC)
    assert start_offset(None, dubai_22) == int(15.5 * 3600)


def test_start_override_and_wrap():
    assert start_offset("18:15") == 10 * 3600 + 15 * 60
    assert clock_to_sim_offset(parse_hhmm("07:45")) == 23 * 3600 + 45 * 60  # last slot of the survey day
    assert clock_to_sim_offset(parse_hhmm("08:00")) == 0
    assert sim_clock_label(10 * 3600 + 15 * 60 + 3, "2026-05-11") == "18:15:03 IST, survey day 2026-05-11"
