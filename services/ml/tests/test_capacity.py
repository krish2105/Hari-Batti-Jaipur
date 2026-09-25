"""v/c table: PM rows from committed aggregates, AM rows from tmc_clean when present."""

import warnings

import pytest

from ml import capacity, data


def test_pm_rows_capacity_formula() -> None:
    rows = [r for r in capacity.vc_table("2026-05-11") if r["period"] == "PM"]
    assert len(rows) == 32  # 8 junctions x 4 approaches
    r = next(r for r in rows if r["junction_id"] == "J03" and r["approach"] == "Sanganer Stadium")
    # J03 plan: C = 60, main green 27, 3 lanes (ASSUMED) -> capacity = 1800*3*27/60 = 2430 PCU/h.
    assert r["cycle_s"] == 60 and r["green_s"] == 27 and r["lanes"] == 3
    assert r["capacity_pcu_h"] == pytest.approx(2430)
    assert r["lanes_source"] == "ASSUMED"
    # PM S + R of Sanganer Stadium comes straight from pm_peak_approach_turns.csv.
    pm = data.load_pm_peak("2026-05-11")["J03"]["Sanganer Stadium"]
    assert r["flow_pcu_h"] == pytest.approx(pm["S"] + pm["R"], abs=0.1)
    assert r["vc"] == pytest.approx((pm["S"] + pm["R"]) / 2430, abs=1e-3)
    assert r["timing_label"] == data.ASSUMED_TIMING_LABEL
    assert r["hour_start"] == "18:15"


def test_flags() -> None:
    for r in capacity.vc_table("2026-05-11"):
        assert r["flag"] == ("over 0.9" if r["vc"] > 0.9 else "")


def test_missing_tmc_gives_pm_only(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(data, "TMC_CSV", tmp_path / "nope.csv")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rows = capacity.vc_table("2026-05-11")
    assert {r["period"] for r in rows} == {"PM"}
    assert any("AM rows skipped" in str(w.message) for w in caught)


@pytest.mark.skipif(not data.TMC_AVAILABLE, reason="tmc_clean.csv is local-only and missing")
def test_am_rows_present() -> None:
    rows = [r for r in capacity.vc_table("2026-05-11") if r["period"] == "AM"]
    assert len(rows) == 32
    j03 = [r for r in rows if r["junction_id"] == "J03"]
    assert {r["hour_start"] for r in j03} == {"09:00"}
    assert all(r["flow_pcu_h"] > 0 for r in rows)


def test_second_day_has_j03_to_j08_only() -> None:
    ids = {r["junction_id"] for r in capacity.vc_table("2026-05-12")}
    assert ids == {"J03", "J04", "J05", "J06", "J07", "J08"}


@pytest.mark.skipif(not data.TMC_AVAILABLE, reason="tmc_clean.csv is local-only and missing")
def test_approach_hours_for_metrics() -> None:
    hours = capacity.approach_hours("2026-05-11")
    assert len(hours) == 8 * 4 * 24
    assert {h.link_length_m for h in hours} == {500.0}
