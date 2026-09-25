"""Shared loaders: registry, lanes, slots, and hourly flows from tmc_clean."""

from collections import defaultdict

import pytest

from ml import data


def test_registry_ids() -> None:
    assert data.junction_ids() == [f"J0{i}" for i in range(1, 9)]


def test_main_and_cross_approaches() -> None:
    assert data.main_approaches("J01") == ("B2BYPASS", "SUMER NAGAR")
    assert data.main_approaches("J05") == ("Mansarover Metro", "Sanganer Stadium")
    assert data.cross_approaches("J03") == ("Patrika Gate", "Sumer Nagar")
    with pytest.raises(KeyError):
        data.main_approaches("J99")


def test_parse_lanes() -> None:
    appr = ("Mansarover Metro", "Sumer Nagar")
    assert data.parse_lanes("", appr) == {}
    assert data.parse_lanes("3", appr) == {"Mansarover Metro": 3, "Sumer Nagar": 3}
    assert data.parse_lanes("Mansarover Metro:3 | sumer nagar:2", appr) == {
        "Mansarover Metro": 3,
        "Sumer Nagar": 2,
    }
    with pytest.raises(ValueError):
        data.parse_lanes("Nowhere:3", appr)


def test_lanes_fallback_is_flagged() -> None:
    # Registry lanes are blank today -> assumptions.toml main 3 / cross 2, marked ASSUMED.
    lanes, source = data.lanes_for("J03")
    assert lanes["Mansarover Metro"] == 3
    assert lanes["Patrika Gate"] == 2
    assert set(source.values()) <= {"ASSUMED", "registry"}


def test_slots() -> None:
    assert data.slot_of("08:00") == 0
    assert data.slot_of("09:15") == 5
    assert data.slot_of("07:45") == 95
    assert data.hour_of_slot(0) == 8
    assert data.hour_of_slot(64) == 0


def test_field_timings_ignore_example() -> None:
    # The only row in signal_timings.csv today is an EXAMPLE row.
    assert "J03" not in data.load_field_timings() or all(
        "EXAMPLE" not in r["notes"].upper() for r in data.load_field_timings()["J03"]
    )


@pytest.mark.skipif(not data.TMC_AVAILABLE, reason="tmc_clean.csv is local-only and missing")
def test_hourly_approach_pcu_matches_hourly_profile() -> None:
    # Summing every approach of a junction-hour must give the committed hourly_profile_pcu.csv.
    hourly = data.hourly_approach_pcu("2026-05-11")
    totals: dict[tuple[str, int], float] = defaultdict(float)
    for (jid, _appr, hour), pcu in hourly.items():
        totals[(jid, hour)] += pcu
    for r in data._read_csv(data.HOURLY_CSV):
        if r["survey_date"] == "2026-05-11":
            assert totals[(r["junction_id"], int(r["hour"]))] == pytest.approx(float(r["total_pcu"]))


def test_load_tmc_missing_message(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(data, "TMC_CSV", tmp_path / "nope.csv")
    data.load_tmc.cache_clear()
    try:
        with pytest.raises(FileNotFoundError, match="local-only"):
            data.load_tmc()
    finally:
        data.load_tmc.cache_clear()
