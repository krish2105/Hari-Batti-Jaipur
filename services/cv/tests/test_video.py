"""Pure parts of the video pipeline: turns, survey slots, stop-line crossing, saturation flow, lamp colour."""

import numpy as np

from hbcv.video import crosses, lamp_colour, saturation_from_headways, slot_of, turn_of


def test_turns_for_left_hand_traffic():
    assert turn_of("S", "W") == "L" and turn_of("S", "N") == "S" and turn_of("S", "E") == "R"
    assert turn_of("E", "S") == "L" and turn_of("W", "S") == "R" and turn_of("N", "N") is None


def test_survey_slots_start_at_eight():
    assert slot_of(8 * 3600) == 0
    assert slot_of(18 * 3600 + 20 * 60) == 41  # 18:15-18:30
    assert slot_of(7 * 3600 + 50 * 60) == 95


def test_crossing_a_stop_line():
    assert crosses((0, 5), (10, 5), (5, 0), (5, 10))
    assert not crosses((0, 5), (4, 5), (5, 0), (5, 10))
    assert not crosses((0, 20), (10, 20), (5, 0), (5, 10))  # passes beside the line


def test_saturation_flow_ignores_start_up_and_isolated_vehicles():
    # one queue: start-up headways 3 s, then a steady 2 s -> 1,800 veh/h
    times = [0, 3, 6, 9, 12] + [12 + 2 * k for k in range(1, 11)]
    r = saturation_from_headways([float(t) for t in times], [True] * len(times))
    assert r["measured"] and r["meanHeadwayS"] == 2.0 and r["vehPerHour"] == 1800
    assert not saturation_from_headways([0.0, 10.0, 20.0], [True, True, True])["measured"]
    assert not saturation_from_headways([float(t) for t in times], [False] * len(times))["measured"]


def _lamp(bgr):
    roi = np.zeros((20, 20, 3), np.uint8)
    roi[5:15, 5:15] = bgr
    return lamp_colour(roi)


def test_lamp_colours():
    assert _lamp((40, 40, 255)) == "RED"
    assert _lamp((40, 200, 40)) == "GREEN"
    assert _lamp((0, 180, 255)) == "AMBER"
    assert _lamp((20, 20, 20)) == "DARK"
