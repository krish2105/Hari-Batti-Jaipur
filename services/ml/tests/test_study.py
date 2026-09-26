"""Field-study analysis (P8 W14): trimming, stop counting, statistics and the SIM cohort."""

from ml.study.analyse import analyse, bootstrap_diff, min_detectable, permutation_p, run_metrics, trim
from ml.study.geo import at_chainage, corridor, project
from ml.study.synth import cohort, run


def drive(speeds: list[float], start_m: float = 0.0) -> list[list[float]]:
    """A 1 Hz trace along the corridor with the given speeds (km/h)."""
    s, out = start_m, []
    for t, v in enumerate(speeds):
        lat, lng = at_chainage(s)
        out.append([float(t), lat, lng, v])
        s += v / 3.6
    return out


def test_projection_round_trip():
    L = corridor()["chainage"][-1]
    for s in (0.0, L / 3, L):
        lat, lng = at_chainage(s)
        got, off = project(lat, lng)
        assert abs(got - s) < 2 and off < 2


def test_trim_and_stop_counting():
    L = corridor()["chainage"][-1]
    cruise = [36.0] * int((L + 600) / 10)
    pts = drive([36.0] * 30 + [2.0] * 5 + [36.0] * len(cruise), start_m=-250)  # one 5 s stop early on
    kept = trim(pts)
    assert len(kept) < len(pts)
    m = run_metrics(pts)
    assert m["valid"] and m["stops"] == 1 and 4 <= m["timeStoppedS"] <= 6
    brief = drive([36.0] * 30 + [2.0] * 2 + [36.0] * len(cruise), start_m=-250)  # 2 s slow is not a stop
    assert run_metrics(brief)["stops"] == 0


def test_statistics_do_not_invent_effects():
    a = [1.0, 2.0, 1.0, 2.0, 1.0, 2.0]
    lo, hi = bootstrap_diff(a, list(a))
    assert lo <= 0 <= hi
    assert permutation_p(a, list(a)) > 0.5
    far_lo, _far_hi = bootstrap_diff([10.0, 11, 12, 10, 11], [1.0, 2, 1, 2, 1])
    assert far_lo > 0 and permutation_p([10.0, 11, 12, 10, 11], [1.0, 2, 1, 2, 1]) < 0.05
    assert round(min_detectable(1.0, 10), 2) == 1.25


def test_sim_cohort_is_balanced_and_labelled():
    runs = cohort()
    assert len(runs) == 20 and sum(r["arm"] == "advice" for r in runs) == 10
    assert all(r["participant"].startswith("SIM-") for r in runs)
    res = analyse(runs[:8], "SIM")
    assert res["source"] == "SIM" and res["runs"] == 8
    assert run("control", 1) == run("control", 1)  # reproducible
