"""Registry, lanes and survey demand come only from the data files."""

import csv

import pytest

from sim.config import CALIBRATION_DATE, TMC_CSV, VALIDATION_DATE
from sim.demand import Movement, load_day, vehicle_mix
from sim.layout import derive_layout
from sim.registry import EXPECTED_IDS, all_coords_present, load_registry, parse_lanes


def test_registry_is_j01_to_j08_and_coords_pending():
    js = load_registry()
    assert [j.id for j in js] == EXPECTED_IDS
    assert all_coords_present(js) is False  # schematic until lat/lng are filled


def test_parse_lanes_formats():
    apps = ("Mansarover Metro", "Sumer Nagar")
    assert parse_lanes("", apps) == {}
    assert parse_lanes("3", apps) == {"Mansarover Metro": 3, "Sumer Nagar": 3}
    assert parse_lanes("Mansarover Metro:4 | Sumer Nagar:2", apps) == {
        "Mansarover Metro": 4,
        "Sumer Nagar": 2,
    }
    with pytest.raises(ValueError):
        parse_lanes("Unknown Road:2", apps)


def test_j04_pm_slot_matches_direct_sum():
    day = load_day(CALIBRATION_DATE)
    m = Movement("J04", "Mansarover Metro", "Sanganer Stadium", "S")
    with TMC_CSV.open(newline="", encoding="utf-8") as f:
        direct = sum(
            float(r["total_veh"])
            for r in csv.DictReader(f)
            if r["junction_id"] == "J04"
            and r["survey_date"] == CALIBRATION_DATE
            and r["slot"] == "41"
            and r["from_approach"] == m.from_approach
            and r["to_approach"] == m.to_approach
        )
    assert day.veh[m][41] == direct > 0  # slot 41 = 18:15-18:30


def test_calibration_and_validation_days_are_separate():
    cal, val = load_day(CALIBRATION_DATE), load_day(VALIDATION_DATE)
    assert cal.junction_ids == [f"J0{i}" for i in range(1, 9)]
    assert val.junction_ids == [f"J0{i}" for i in range(3, 9)]  # J01/J02: no 12 May data


def test_vehicle_mix_sums_to_one_and_is_half_two_wheelers():
    mix = vehicle_mix(load_day(CALIBRATION_DATE))
    assert sum(mix.values()) == pytest.approx(1.0)
    assert 0.4 < mix["two_wheeler"] < 0.6


def test_layout_from_turn_labels_is_consistent():
    day = load_day(CALIBRATION_DATE)
    lay = derive_layout("J04", list(day.veh))
    assert lay.approach_at == {
        "W": "Mansarover Metro",
        "N": "Durgapur",
        "E": "Sanganer Stadium",
        "S": "Mohanpura",
    }
    assert lay.inconsistencies == ()
