"""Webster cycle, green split, delay terms and the assumed 2-phase plan, against hand-worked examples."""

import pytest

from ml import data
from ml.webster import incremental_delay, split_greens, two_phase_plan, uniform_delay, webster_cycle


def test_webster_cycle_hand_example() -> None:
    # y = [0.4, 0.35] -> Y = 0.75; L = 8 s. C0 = (1.5*8 + 5) / (1 - 0.75) = 17 / 0.25 = 68 s.
    assert webster_cycle([0.4, 0.35], 8) == (pytest.approx(68.0), False)
    # y = [0.3, 0.3] -> C0 = 17 / 0.4 = 42.5 s: raw value without clamp, 60 s with the default clamp.
    assert webster_cycle([0.3, 0.3], 8, min_c=0)[0] == pytest.approx(42.5)
    assert webster_cycle([0.3, 0.3], 8) == (60, False)


def test_webster_cycle_oversaturated() -> None:
    # Y = 1.05 >= 1: no fixed cycle works -> max cycle, oversaturated flag.
    assert webster_cycle([0.6, 0.45], 8) == (180, True)


def test_split_greens_proportional_and_min_green() -> None:
    # 50 s shared 0.3 : 0.1 -> 37.5 / 12.5 -> round() gives 38 / 12 (sum stays 50).
    assert split_greens([0.3, 0.1], 50) == [38, 12]
    # 0.5 : 0.02 -> 48.1 / 1.9; the small phase is lifted to the 10 s minimum, the other gets 40.
    assert split_greens([0.5, 0.02], 50) == [40, 10]


def test_uniform_delay_hand_example() -> None:
    # C = 60, g = 30 (g/C = 0.5), x = 0.8: d1 = 0.5*60*(0.5)^2 / (1 - 0.8*0.5) = 7.5 / 0.6 = 12.5 s.
    assert uniform_delay(60, 30, 0.8) == pytest.approx(12.5)
    # x = 1.2 is capped at 1: d1 = 7.5 / (1 - 0.5) = 15 s.
    assert uniform_delay(60, 30, 1.2) == pytest.approx(15.0)


def test_incremental_delay_hand_example() -> None:
    # x = 1, c = 1800, T = 0.25: d2 = 900*0.25*(0 + sqrt(4*1/(1800*0.25))) = 225*sqrt(0.008889)
    #   = 225 * 0.094281 = 21.213 s.
    assert incremental_delay(1.0, 1800) == pytest.approx(21.2132, abs=1e-3)
    # x = 0.5, c = 1000: (x-1) = -0.5; sqrt(0.25 + 2/250) = sqrt(0.258) = 0.507937
    #   d2 = 225 * (0.507937 - 0.5) = 225 * 0.007937 = 1.786 s.
    assert incremental_delay(0.5, 1000) == pytest.approx(1.7858, abs=1e-3)


def test_two_phase_plan_hand_example() -> None:
    # Main: A S+R = 1620 on 3 lanes -> y = 1620/5400 = 0.3 (B is quieter).
    # Cross: C S+R = 1080 on 2 lanes -> y = 1080/3600 = 0.3 (D is quieter).
    # Y = 0.6, L = 2*4 = 8 -> C0 = 42.5 -> 60 s. Total green = 60 - 2*(3+2) = 50 -> 25 / 25.
    a = data.load_assumptions()
    pcu = {
        "A": {"L": 500, "S": 1200, "R": 420},
        "B": {"L": 100, "S": 800, "R": 100},
        "C": {"L": 999, "S": 700, "R": 380},
        "D": {"L": 0, "S": 300, "R": 100},
    }
    lanes = {"A": 3, "B": 3, "C": 2, "D": 2}
    plan = two_phase_plan(pcu, ("A", "B"), lanes, a)
    assert plan["cycle_s"] == 60
    assert plan["green_s"] == {"A": 25, "B": 25, "C": 25, "D": 25}
    assert plan["Y"] == pytest.approx(0.6)
    assert plan["oversaturated"] is False
    assert plan["label"] == "Assumed timing – demand-proportional (2-phase, free left)"


@pytest.mark.parametrize(
    ("jid", "cycle", "main_green", "cross_green", "over"),
    [("J03", 60, 27, 23, False), ("J06", 117, 62, 45, False), ("J01", 180, 60, 110, True)],
)
def test_two_phase_plan_matches_simulator(
    jid: str, cycle: int, main_green: int, cross_green: int, over: bool
) -> None:
    # Reference values from services/sim/sim/timings.py (sim calibration report, 11 May PM peak).
    pm = data.load_pm_peak("2026-05-11")[jid]
    lanes, _ = data.lanes_for(jid)
    main = data.main_approaches(jid)
    plan = two_phase_plan(pm, main, lanes, data.load_assumptions())
    assert plan["cycle_s"] == cycle
    assert plan["oversaturated"] is over
    for name in main:
        assert plan["green_s"][name] == main_green
    for name in data.cross_approaches(jid):
        assert plan["green_s"][name] == cross_green
