"""Signal plans: FIELD rows win, EXAMPLE rows are ignored, Webster maths matches hand examples."""

import pytest

from sim.config import load_assumptions
from sim.timings import (
    PLAN_LABELS,
    choose_plan,
    load_field_rows,
    plan_even,
    plan_two_phase,
    plan_webster4,
    split_greens,
    webster_cycle,
)

A = load_assumptions()
SIDE_OF = {"Metro": "W", "North Rd": "N", "Stadium": "E", "South Rd": "S"}
LANES = {"Metro": 3, "North Rd": 2, "Stadium": 3, "South Rd": 2}


def test_example_row_is_ignored(tmp_path):
    f = tmp_path / "t.csv"
    f.write_text(
        "junction_id,date,time_window,phase_no,approaches_served,green_s,amber_s,all_red_s,cycle_s,signal_mode,notes\n"
        "J03,2026-10-05,18:15-18:45,1,Mansarover Metro (S+L),45,3,2,150,FIXED,EXAMPLE ROW - delete\n"
    )
    assert load_field_rows(f) == {}


def test_real_rows_give_field_plan(tmp_path):
    f = tmp_path / "t.csv"
    f.write_text(
        "junction_id,date,time_window,phase_no,approaches_served,green_s,amber_s,all_red_s,cycle_s,signal_mode,notes\n"
        "J03,2026-10-05,18:15-18:45,1,Metro (S+L); Stadium (S+L),40,3,2,90,FIXED,\n"
        "J03,2026-10-05,18:15-18:45,2,North Rd; South Rd,40,3,2,90,FIXED,\n"
    )
    rows = load_field_rows(f)
    plan = choose_plan("demand2", "J03", SIDE_OF, LANES, {}, rows, A)
    assert plan.timing == "FIELD"
    assert plan.cycle_s == 90
    assert plan.phases[0].moves == {("W", "S"): "G", ("W", "L"): "G", ("E", "S"): "G", ("E", "L"): "G"}


def test_even_split_is_4_by_30_seconds():
    p = plan_even("J03", A)
    assert p.cycle_s == 120
    assert [ph.duration_s for ph in p.phases if ph.kind == "green"] == [25, 25, 25, 25]
    assert p.label == "Assumed timing – even split"


def test_webster_cycle_hand_example():
    # y = 0.3 + 0.2 = 0.5, L = 8 s -> C0 = (1.5*8 + 5) / 0.5 = 34 s -> clamped up to 60 s
    assert webster_cycle([0.3, 0.2], 8, 60, 180) == (60, False)
    # y = 0.45 + 0.35 = 0.8, L = 8 -> C0 = 17 / 0.2 = 85 s
    c, over = webster_cycle([0.45, 0.35], 8, 60, 180)
    assert c == pytest.approx(85.0) and over is False


def test_webster_oversaturated_caps_at_180():
    assert webster_cycle([0.6, 0.5], 16, 60, 180) == (180, True)


def test_split_greens_proportional_with_minimum():
    assert split_greens([0.45, 0.35], 75, 10) == [42, 33]  # 75 * 0.45/0.8 = 42.2, 75 * 0.35/0.8 = 32.8
    g = split_greens([0.60, 0.02], 50, 10)
    assert g == [40, 10] and sum(g) == 50  # tiny phase gets the 10 s minimum


def test_two_phase_hand_example():
    # main: max((1000+200)/(3*1800), (900+100)/(3*1800)) = 0.2222; cross: max((500+100)/(2*1800), ...) = 0.1667
    pm = {
        "Metro": {"L": 300, "S": 1000, "R": 200},
        "Stadium": {"L": 200, "S": 900, "R": 100},
        "North Rd": {"L": 100, "S": 500, "R": 100},
        "South Rd": {"L": 100, "S": 300, "R": 100},
    }
    p = plan_two_phase("J03", SIDE_OF, LANES, pm, A)
    assert p.webster_y == pytest.approx(0.389, abs=1e-3)
    assert p.cycle_s == 60  # C0 = 17 / 0.611 = 27.8 s -> minimum 60 s
    greens = [ph.duration_s for ph in p.phases if ph.kind == "green"]
    assert greens == [29, 21]  # 50 s of green split 0.2222 : 0.1667
    assert p.label == PLAN_LABELS["demand2"] == "Assumed timing – demand-proportional (2-phase, free left)"
    # free left: every left turn is green in every phase
    assert all(ph.moves.get((s, "L")) == "G" for ph in p.phases for s in "WNES")
    # right turns only permitted (give way)
    assert p.phases[0].moves[("W", "R")] == "g"


def test_webster4_flags_oversaturation():
    pm = {n: {"L": 800, "S": 1500, "R": 700} for n in SIDE_OF}
    p = plan_webster4("J03", SIDE_OF, LANES, pm, A)
    assert p.oversaturated and p.cycle_s == 180
    assert "demand exceeds 4-stage capacity" in p.notes[0]
