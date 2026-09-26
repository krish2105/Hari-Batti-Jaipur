"""The simulator's calibrated settings (W1): read from calibrated.json, labelled, never silent."""

import json

from sim.calibrate_opt import calibrated_payload
from sim.config import calibrated_overrides

BEST = {
    "trial": 1,
    "params": {
        "main_lanes": 4,
        "cross_lanes": 3,
        "tau_s": 1.0,
        "two_wheeler_min_gap_lat_m": 0.3,
        "speed_factor": 1.0,
        "turn_lanes": "auto",
    },
    "calibration_geh_share": 0.465,
    "validation_geh_share": 0.44,
    "unserved_share": 0.19,
}


def test_no_file_means_plain_assumptions(tmp_path):
    assert calibrated_overrides(tmp_path / "missing.json") == (None, None)


def test_file_gives_overrides_and_a_visible_flag(tmp_path):
    p = tmp_path / "calibrated.json"
    p.write_text(json.dumps(calibrated_payload(BEST)), encoding="utf-8")
    over, flag = calibrated_overrides(p)
    assert over["lanes"] == {"main_road": 4, "cross_road": 3}
    assert over["network"]["midblock_access"] is False
    assert over["vehicles"]["tau_s"] == 1.0
    assert "trial 1" in flag and "ASSUMED" in flag and "4" in flag


def test_payload_records_scores_and_that_validation_was_not_used():
    p = calibrated_payload(BEST)
    assert p["trial"] == 1
    assert p["scores"]["calibration_geh_share"] == 0.465
    assert "12 May" in p["note"]
