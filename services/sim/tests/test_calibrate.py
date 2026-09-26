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


def test_w1_sections_label_assumed_and_field_and_show_the_search(tmp_path):
    from sim.calibrate import w1_sections

    manifest = {
        "geometry": "SCHEMATIC",
        "assumptions": {
            "lanes": {"main_road": 4, "cross_road": 3},
            "capacity": {"saturation_flow_pcu_per_lane_h": 1800},
            "vehicles": {"tau_s": 1.0, "speed_factor": 1.0},
            "sublane": {"two_wheeler_min_gap_lat_m": 0.3},
            "geometry": {"link_spacing_m": 500},
        },
        "plans": {"demand2": {"J05": {"timing": "ASSUMED"}}},
    }
    diag = {
        "saturation": {"survey mix, sublane on": {"pcu_per_green_h_per_lane": 1909}},
        "variants": [{"id": "V0", "label": "start", "calibration_geh_share": 0.28, "validation_geh_share": 0.2,
                      "unserved_share": 0.42, "teleports": 924}],
    }  # fmt: skip
    trials = "trial,main_lanes,calibration_geh_share,validation_geh_share,unserved_share\n1,4,0.465,0.44,0.19\n0,3,0.35,0.28,0.32\n"
    best = {"trial": 1, "calibration_geh_share": 0.465, "trials": 2}
    text = "\n".join(w1_sections(manifest, 0.07, diag, trials, best))
    assert "| Signal timings | Assumed timing" in text
    assert "Traffic counts (demand, vehicle mix) | Survey, May 2026 | FIELD" in text
    assert "7%" in text and "FAIL" in text  # unserved demand vs the 5% target
    assert "V0" in text and "1,909" in text
    assert text.index("| 1 |") < text.index("| 0 |")  # trials ranked by the calibration day only
