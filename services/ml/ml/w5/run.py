"""Run W5 end to end and write reports/forecasting.md, forecast.json and anomalies.json.

Real survey (2 days): train on 11 May, test on 12 May, J03-J08 movements (J01-J02 have one day).
SIM (8 weeks generated from the 11 May profile): train weeks 1-6, calibration/early-stopping week 7,
test week 8. Deep learning is trained and tested on SIM only.
Run: uv run --group forecast python -m ml.w5.run
"""

import itertools
import json
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from .. import data
from ..forecast import _series
from . import anomaly
from .models import (
    SLOTS,
    conformal_q,
    feature_rows,
    gwn_lite,
    level_adjusted,
    lightgbm,
    metrics,
    shap_importance,
)
from .simdemand import generate

REPORTS = Path(__file__).resolve().parents[2] / "reports"
CORRIDOR = ["J08", "J07", "J06", "J05", "J04", "J03"]
RECORDS = data.ROOT / "services" / "sim" / "build" / "opt" / "eval"


def _score(label: str, id_: str, y: np.ndarray, p: np.ndarray, baseline: bool = False) -> dict:
    m = metrics(y, p)
    return {
        "id": id_,
        "label": label,
        "mae": round(m["mae"], 2),
        "rmse": round(m["rmse"], 2),
        "wape": round(m["wape"], 4),
        "isBaseline": baseline,
    }


def real_block() -> tuple[dict, list[tuple[str, int]], np.ndarray, np.ndarray]:
    series = _series()
    keys = list(series)
    jidx = {j: i for i, j in enumerate(sorted({k[0] for k in keys}))}
    d1 = np.array([series[k]["2026-05-11"] for k in keys])
    d2 = np.array([series[k]["2026-05-12"] for k in keys])
    xs_tr, ys_tr, xs_te, ys_te, naive, level, last = [], [], [], [], [], [], []
    for m, k in enumerate(keys):
        tl = np.concatenate([d1[m], d2[m]])
        xs_tr.append(feature_rows(tl, range(4, SLOTS), m, jidx[k[0]], week=False))
        ys_tr.append(tl[4:SLOTS])
        xs_te.append(feature_rows(tl, range(SLOTS, 2 * SLOTS), m, jidx[k[0]], week=False))
        ys_te.append(tl[SLOTS:])
        naive.append(tl[:SLOTS])
        level.append([level_adjusted(tl, tl, i) for i in range(SLOTS, 2 * SLOTS)])
        last.append(tl[SLOTS - 1 : 2 * SLOTS - 1])
    x_tr, y_tr, x_te, y_te = np.vstack(xs_tr), np.concatenate(ys_tr), np.vstack(xs_te), np.concatenate(ys_te)
    model = lightgbm(x_tr, y_tr)
    pred = np.clip(model.predict(x_te), 0, None)
    block = {
        "data": "SURVEY",
        "train": "Survey 11 May 2026 (1 day)",
        "test": "Survey 12 May 2026 (1 day)",
        "nTrain": int(y_tr.size),
        "nTest": int(y_te.size),
        "series": len(keys),
        "models": [
            _score("Seasonal naive (same slot yesterday)", "naive-day", y_te, np.concatenate(naive), True),
            _score("Last value (previous 15 min)", "last", y_te, np.concatenate(last), True),
            _score("Level-adjusted profile", "profile", y_te, np.concatenate(level), True),
            _score("LightGBM (1 training day)", "lightgbm", y_te, pred),
        ],
    }
    return block, keys, d1, d2


def sim_block(keys: list[tuple[str, int]], profile: np.ndarray) -> tuple[dict, dict, dict, list[dict]]:
    sim = generate(profile, keys, seed=7)
    counts = sim.counts
    n, t = counts.shape
    train_end, val_end = 42 * SLOTS, 49 * SLOTS
    jidx = {j: i for i, j in enumerate(sorted({k[0] for k in keys}))}
    parts = {"tr": ([], []), "va": ([], []), "te": ([], [])}
    for m, k in enumerate(keys):
        for name, rng in (
            ("tr", range(7 * SLOTS, train_end)),
            ("va", range(train_end, val_end)),
            ("te", range(val_end, t)),
        ):
            parts[name][0].append(feature_rows(counts[m], rng, m, jidx[k[0]]))
            parts[name][1].append(counts[m, rng.start : rng.stop])
    (x_tr, y_tr), (x_va, y_va), (x_te, y_te) = ((np.vstack(a), np.concatenate(b)) for a, b in parts.values())
    model = lightgbm(x_tr, y_tr, x_va, y_va)
    p_va = np.clip(model.predict(x_va), 0, None)
    p_te = np.clip(model.predict(x_te), 0, None)
    # baselines on the test week, flattened in the same (movement, step) order
    yday = np.concatenate([counts[m, val_end - SLOTS : t - SLOTS] for m in range(n)])
    week = np.concatenate([counts[m, val_end - 7 * SLOTS : t - 7 * SLOTS] for m in range(n)])
    wk = (
        counts[:, 7 * SLOTS : train_end].reshape(n, -1, 7, SLOTS).mean(axis=1)
    )  # (n, weekday, slot) in training weeks
    dows = (np.arange(val_end, t) // SLOTS) % 7
    prof = np.concatenate([wk[m, dows, np.arange(val_end, t) % SLOTS] for m in range(n)])
    # GWN-lite over all movements at once
    adj = np.eye(n)
    for a, ka in enumerate(keys):
        for b, kb in enumerate(keys):
            if a != b:
                if ka[0] == kb[0]:
                    adj[a, b] = 1.0
                elif abs(CORRIDOR.index(ka[0]) - CORRIDOR.index(kb[0])) == 1:
                    adj[a, b] = 0.5
    # PyTorch runs in its own spawned process: LightGBM and PyTorch each ship an OpenMP runtime, and
    # two of them in one macOS process can deadlock
    ctx = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(1, mp_context=ctx) as pool:
        p_gwn, gwn_info = pool.submit(gwn_lite, counts, adj, train_end, val_end, 16, 12).result()
    q = conformal_q(np.abs(y_va - p_va), 0.9)
    covered = float(np.mean(np.abs(y_te - p_te) <= q))
    sample = np.random.default_rng(0).choice(len(x_te), size=min(5000, len(x_te)), replace=False)
    block = {
        "data": "SIM",
        "train": "SIM weeks 1-6 (generated from the 11 May survey profile)",
        "test": "SIM week 8 (week 7 used for early stopping and conformal calibration)",
        "nTrain": int(y_tr.size),
        "nTest": int(y_te.size),
        "series": n,
        "models": [
            _score("Seasonal naive (same slot yesterday)", "naive-day", y_te, yday, True),
            _score("Weekly naive (same slot last week)", "naive-week", y_te, week, True),
            _score("Weekday profile (training weeks)", "profile", y_te, prof, True),
            _score("LightGBM", "lightgbm", y_te, p_te),
            _score("GWN-lite (Graph WaveNet-style, simplified)", "gwn-lite", y_te, p_gwn.reshape(-1)),
        ],
        "gwn": gwn_info,
    }
    conformal = {"target": 0.9, "empirical": round(covered, 4), "meanWidthVeh": round(2 * q, 1), "halfWidthVeh": round(q, 1),
                 "data": "SIM", "method": "split conformal on LightGBM absolute errors (calibration: SIM week 7)"}  # fmt: skip
    shap = shap_importance(model, x_te[sample])
    # anomalies on the test week vs the weekday profile
    exp_te = np.stack([wk[m, dows, np.arange(val_end, t) % SLOTS] for m in range(n)])
    steps_tr = np.arange(7 * SLOTS, train_end)
    exp_tr = wk[:, (steps_tr // SLOTS) % 7, steps_tr % SLOTS]
    groups = np.array([k[0] for k in keys])
    exp_te = anomaly.level_adjust(counts[:, val_end:], exp_te, groups)
    exp_tr = anomaly.level_adjust(counts[:, 7 * SLOTS : train_end], exp_tr, groups)
    found = anomaly.detect(counts[:, val_end:], exp_te, counts[:, 7 * SLOTS : train_end], exp_tr)
    inj = anomaly.score_injected(found, sim.anomalies, val_end, t - val_end, exp_te, 10.0)
    inj["all"] = anomaly.score_injected(
        found, sim.anomalies, val_end, t - val_end
    )  # including near-empty movements
    by_kind = {}
    for kind in ("incident", "surge", "closure"):
        by_kind[kind] = anomaly.score_injected(
            found, [a for a in sim.anomalies if a["kind"] == kind], val_end, t - val_end, exp_te, 10.0
        )["recall"]
    return block, conformal, {"injected": inj, "recallByKind": by_kind}, shap


def real_anomalies(keys, d1, d2) -> list[dict]:
    """12 May vs the 11 May profile (scaled by the day's total), top findings with plain explanations."""
    wanted = set(keys)
    names = {}
    for r in data.load_tmc():
        k = (r["junction_id"], r["movement"])
        if k in wanted:
            names[k] = (r["from_approach"], r["to_approach"], r["turn"])
    ratio = d2.sum() / max(1.0, d1.sum())
    expected = d1 * ratio
    groups = np.array([k[0] for k in keys])
    expected = anomaly.level_adjust(d2, expected, groups)
    found = anomaly.detect(d2, expected, d1, anomaly.level_adjust(d1, d1.copy(), groups))
    z = anomaly.zscores(d2, expected)
    items = []
    for (r, s), (kind, _score) in sorted(found.items(), key=lambda kv: -abs(z[kv[0]]))[:15]:
        j, _m = keys[r]
        f, to, turn = names.get(keys[r], ("?", "?", "?"))
        clock = (8 + s // 4) % 24
        pct = 100 * (d2[r, s] - expected[r, s]) / max(1.0, expected[r, s])
        m0 = (s % 4) * 15
        # percentages only: a single 15-min movement count is a raw survey row and stays confidential
        detail = f"{f} → {to} ({turn}), {clock:02d}:{m0:02d}-{clock:02d}:{m0 + 15:02d}: {pct:+.0f}% vs the 11 May profile"
        items.append(
            {
                "junctionId": j,
                "date": "2026-05-12",
                "hour": clock,
                "kind": kind,
                # relative deviation, not the z-score: z together with the % would reveal the raw count
                "score": round(abs(pct) / 100, 2),
                "detail": detail,
            }
        )
    return items


def phase_change() -> dict | None:
    """Seconds until the current stage ends, from the corridor PPO agent's stage logs (W2, SIM):
    predict with the median remaining time for the elapsed time so far (AM peak logs), calibrate a
    conformal band on midday, test coverage on the PM peak."""
    recs = {p: RECORDS.glob(f"record-*-{p}/result.json") for p in ("AM", "Mi", "PM")}
    logs = {}
    for p, files in recs.items():
        f = next(iter(files), None)
        if f is None:
            return None
        logs[p] = json.loads(f.read_text())["stages"]
    dt = 6

    def pairs(period):
        out = []
        for seq in logs[period].values():
            runs, cur = [], 1
            for a, b in itertools.pairwise(seq):
                if a == b:
                    cur += 1
                else:
                    runs.append(cur)
                    cur = 1
            for r in runs:
                out += [(e * dt, (r - e) * dt) for e in range(r)]
        return np.array(out, float)

    tr, ca, te = pairs("AM"), pairs("Mi"), pairs("PM")
    bins = np.arange(0, 181, 6)
    med = np.array(
        [
            np.median(tr[(tr[:, 0] >= b) & (tr[:, 0] < b + 6), 1])
            if ((tr[:, 0] >= b) & (tr[:, 0] < b + 6)).any()
            else np.median(tr[:, 1])
            for b in bins
        ]
    )

    def predict(e):
        return med[np.clip((e // 6).astype(int), 0, len(med) - 1)]

    q = conformal_q(np.abs(ca[:, 1] - predict(ca[:, 0])), 0.9)
    err = np.abs(te[:, 1] - predict(te[:, 0]))
    return {"data": "SIM", "target": 0.9, "empirical": round(float(np.mean(err <= q)), 4), "halfWidthS": round(q, 1),
            "maeS": round(float(err.mean()), 1), "nTest": len(te),
            "method": "median remaining stage time given elapsed time (PPO corridor agent logs, AM peak) + split conformal (midday); tested on the PM peak"}  # fmt: skip


def write_md(fc: dict, an: dict) -> str:
    def table(block):
        rows = ["| Model | MAE | RMSE | WAPE |", "| --- | --- | --- | --- |"]
        best = min(m["wape"] for m in block["models"])
        for m in block["models"]:
            flag = " (baseline)" if m["isBaseline"] else ""
            w = f"**{100 * m['wape']:.1f}%**" if m["wape"] == best else f"{100 * m['wape']:.1f}%"
            rows.append(f"| {m['label']}{flag} | {m['mae']:.2f} | {m['rmse']:.2f} | {w} |")
        return rows

    r, s, c = fc["real"], fc["sim"], fc["conformal"]
    lg_r = next(m for m in r["models"] if m["id"] == "lightgbm")
    best_r_base = min((m for m in r["models"] if m["isBaseline"]), key=lambda m: m["wape"])
    L = [
        "# HariBatti — demand forecasting and anomaly detection (W5)",
        "",
        (
            f"> Generated {datetime.now(UTC).astimezone(ZoneInfo('Asia/Kolkata')):%Y-%m-%d %H:%M} IST · 15-minute-ahead forecasts of vehicles per junction movement (J03–J08) · "
            "MAE and RMSE in vehicles per 15 min, WAPE = total absolute error ÷ total vehicles"
        ),
        "",
        "## 1. Real survey data — only 2 days, so be careful",
        "",
        (
            f"**Data-quality finding:** the 12 May counts correlate {fc['dataQuality']['correlation']:.4f} with 11 May, "
            f"{100 * fc['dataQuality']['identicalShare']:.0f}% of movement-slots are exactly identical and the median ratio is "
            f"{fc['dataQuality']['medianRatio']:.3f}. 12 May looks largely derived from 11 May, so it is not an independent "
            "test day: the naive and profile baselines look near-perfect for that reason, not because traffic is that predictable. "
            "This question has been raised for the survey agency (data/README.md)."
        ),
        "",
        f"Train: {r['train']} ({r['nTrain']:,} movement-slots). Test: {r['test']} ({r['nTest']:,}). {r['series']} movements. **Survey, May 2026.**",
        "",
        *table(r),
        "",
        f"LightGBM WAPE {100 * lg_r['wape']:.1f}% vs the best baseline ({best_r_base['label']}) {100 * best_r_base['wape']:.1f}%. "
        + (
            "It beats the baseline on this one test day, "
            if lg_r["wape"] < best_r_base["wape"]
            else "It does **not** beat the baseline, "
        )
        + "but one training day and one test day prove nothing about next month: no deep-learning claim is made on real data.",
        "",
        "## 2. SIM data — 8 generated weeks",
        "",
        (
            f"{s['train']}; {s['test']}. {s['nTrain']:,} training and {s['nTest']:,} test movement-slots. **SIM: trained on simulated data.** "
            "The generator (ml/w5/simdemand.py) starts from the 11 May survey profile and adds ASSUMED weekday factors, day and "
            "slot noise, rain days, evening events and labelled incidents; results show whether the pipeline works, not how "
            "accurate it would be on real weeks."
        ),
        "",
        *table(s),
        "",
        f"GWN-lite: {s['gwn']['parameters']:,} parameters, trained {s['gwn']['epochs']} epochs on {s['gwn']['device']}, best epoch chosen on week 7.",
        "",
        "### Calibrated uncertainty (split conformal, SIM)",
        "",
        (
            f"A ±{c['halfWidthVeh']:.1f}-vehicle band around the LightGBM forecast, sized on week 7, covered **{100 * c['empirical']:.1f}%** "
            f"of week-8 movement-slots (target {100 * c['target']:.0f}%)."
        ),
        "",
    ]
    if fc.get("phaseChange"):
        p = fc["phaseChange"]
        L += [
            "### Time until the next phase change (SIM)",
            "",
            (
                f"{p['method']}. Mean error {p['maeS']:.1f} s; a ±{p['halfWidthS']:.0f} s band covered **{100 * p['empirical']:.1f}%** "
                f"of {p['nTest']:,} test moments (target 90%). This is the band the app shows as a range when confidence is low."
            ),
            "",
        ]
    L += [
        "### What drives the LightGBM forecast (mean |SHAP|, SIM test week)",
        "",
        "| Feature | Mean abs SHAP |",
        "| --- | --- |",
    ]
    L += [f"| {x['feature']} | {x['meanAbsShap']:.3f} |" for x in fc["shap"][:8]]
    inj = an["injected"]
    L += [
        "",
        "## 3. Anomaly detection",
        "",
        (
            f"On SIM week 8 with injected anomalies on movements carrying at least 10 vehicles per 15 min: event recall **{100 * inj['recall']:.0f}%** "
            f"({inj['n']} injected: incidents {100 * an['recallByKind']['incident']:.0f}%, surges {100 * an['recallByKind']['surge']:.0f}%, "
            f"closures {100 * an['recallByKind']['closure']:.0f}%). Alarm precision **{100 * inj['alarmPrecision']:.0f}%** "
            f"({inj['alarms']} alarms; an alarm = consecutive flagged slots on one movement), slot precision "
            f"{100 * inj['precision']:.0f}% ({inj['flagged']} slots). Rain days and evening events are real but unlabelled, "
            f"so some alarms counted as false are genuine. {an['method']}"
        ),
        "",
        "Real survey (12 May vs the 11 May profile) — top findings, **Survey, May 2026**:",
        "",
        "| Junction | Time | Kind | Deviation | What |",
        "| --- | --- | --- | --- | --- |",
    ]
    L += [
        f"| {a['junctionId']} | {a['hour']:02d}:00 | {a['kind']} | {100 * a['score']:.0f}% | {a['detail']} |"
        for a in an["items"][:10]
    ]
    if not an["items"]:
        L.append("| — | — | none | — | No unusual movement-slots: expected, because 12 May is almost a copy of 11 May (section 1). |")
    L += [
        "",
        "## Honest limitations",
        "",
        "- Two survey days: real-data results are one train day and one test day; they cannot show weekly or seasonal skill.",
        (
            "- The SIM weeks come from a generator with ASSUMED patterns, so SIM accuracy is an upper bound on what the pipeline "
            "could do with real weeks of counts (from the CV pipeline or an ITMS feed)."
        ),
        "- GWN-lite is a small, simplified Graph WaveNet-style model (dilated causal convolutions + graph convolution), not the full published architecture.",
        "",
        "Reproduce: `cd services/ml && uv run --group forecast python -m ml.w5.run`",
        "",
    ]
    return "\n".join(L)


def main() -> None:
    real, keys, d1, d2 = real_block()
    sim, conformal, sim_anom, shap = sim_block(keys, d1)
    fc = {"name": "forecast", "source": "SURVEY + SIM", "horizonMin": 15, "real": real, "sim": sim, "conformal": conformal, "shap": shap,
          "phaseChange": phase_change(),
          "note": "Real data: 1 training day and 1 test day (Survey, May 2026). Deep learning trained and tested on SIM data only."}  # fmt: skip
    items = real_anomalies(keys, d1, d2)
    busy = d1 > 20
    fc["dataQuality"] = {
        "correlation": round(float(np.corrcoef(d1.ravel(), d2.ravel())[0, 1]), 5),
        "identicalShare": round(float(np.mean(d1 == d2)), 3),
        "medianRatio": round(float(np.median(d2[busy] / d1[busy])), 3),
        "note": "12 May counts are almost a copy of 11 May (see data/README.md). 12 May is therefore not an "
        "independent test day, and real-data scores (and W1/W2 validation on 12 May) overstate skill.",
    }
    an = {"name": "anomalies", "source": "SURVEY", "method": "Poisson z-score rules (closed, drop, surge) + isolation forest (scikit-learn)",
          "items": items, "injected": {**sim_anom["injected"], "data": "SIM"}, "recallByKind": sim_anom["recallByKind"],
          "note": "Real items compare 12 May with the 11 May profile; live signal faults (stuck, dark, flashing amber) are on the dashboard live wall."}  # fmt: skip
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "forecast.json").write_text(json.dumps(fc, indent=2) + "\n")
    (REPORTS / "anomalies.json").write_text(json.dumps(an, indent=2) + "\n")
    (REPORTS / "forecasting.md").write_text(write_md(fc, an))
    print(json.dumps({"real": [(m["id"], m["wape"]) for m in real["models"]], "sim": [(m["id"], m["wape"]) for m in sim["models"]],
                      "conformal": conformal["empirical"], "anomaly": sim_anom["injected"]}, indent=1))  # fmt: skip


if __name__ == "__main__":
    main()
