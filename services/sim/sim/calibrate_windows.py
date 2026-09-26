"""W1 full-day calibration in windows -> services/sim/reports/calibration.md.

Why windows: a single continuous 24-h run of the schematic network never recovers once the morning
peak overflows it. The backlog of vehicles waiting to enter grows every hour (145,000 by 18:00;
reports/calibration_continuous.json), so later hours measure the backlog rather than the network,
and the run takes most of a day. Instead the day is scored as eight 3-hour windows, run in
parallel, each after a 30-minute warm-up with the same evaluator the calibration search used.
Hour 08-09 has no earlier traffic to warm up from and is shown but not scored.
11 May = calibration (the demand was fitted to it); 12 May = validation (never used to choose).
Run: uv run python -m sim.calibrate_windows
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import config
from .build import build, load_manifest
from .calibrate import (
    GEH_OK,
    TARGET_SHARE,
    WARMUP_HOURS,
    compare,
    demand_fit,
    hour_label,
    lane_load,
    report_header,
    share_ok,
    verdict,
    w1_sections,
)  # fmt: skip
from .evaluate import run_window

WINDOWS = [(h, 3) for h in range(0, 24, 3)]
WARMUP_MIN = 30


def run_day(build_dir: Path, workers: int = 8) -> list[dict]:
    with ThreadPoolExecutor(workers) as pool:
        return list(pool.map(lambda w: run_window(build_dir, w[0], w[1], warmup_min=WARMUP_MIN), WINDOWS))


def sim_turns(runs: list[dict]) -> dict[tuple[str, str, int], float]:
    out: dict[tuple[str, str, int], float] = {}
    for r in runs:
        for k, v in r["turns"].items():
            a, b, h = k.split("|")
            out[(a, b, int(h))] = v
    return out


def write(build_dir: Path, runs: list[dict], runtime_s: float) -> Path:
    m = load_manifest(build_dir)
    sim = sim_turns(runs)
    cal = compare(m, sim, config.CALIBRATION_DATE, 24)
    val = compare(m, sim, config.VALIDATION_DATE, 24)
    scored = lambda rows: [r for r in rows if r["hour"] >= WARMUP_HOURS]
    js = list(m["approaches"])
    val_js = sorted({r["junction"] for r in val})
    loaded = sum(r["vehicles"].get("loaded", 0) for r in runs)
    waiting = sum(r["vehicles"].get("waiting", 0) for r in runs)
    tele = sum(r["teleports"] for r in runs)
    cont_path = config.REPORTS_DIR / "calibration_continuous.json"
    cont = json.loads(cont_path.read_text()) if cont_path.exists() else None

    L = report_header(m, "demand2", 24, runtime_s)
    L += [
        (
            f"**Method:** the survey day is scored as {len(WINDOWS)} three-hour windows run in parallel, each after a "
            f"{WARMUP_MIN}-minute warm-up (a continuous 24-h run never recovers from the morning backlog; see Gridlock). "
            "Counts marked **Survey, May 2026** come from `data/processed/tmc_clean.csv` (hourly aggregates only); **SIM** is "
            f"simulated. GEH = √(2(M−C)²/(M+C)). Target: GEH < {GEH_OK:g} for at least {TARGET_SHARE:.0%} of movement-hours. "
            "Hour 08–09 has no earlier traffic to warm up from and is shown but not scored."
        ),
        "",
        "## Summary",
        "",
        "| Junction | Calibration (11 May) GEH<5 | Result | Validation (12 May) GEH<5 | Result |",
        "| --- | --- | --- | --- | --- |",
    ]
    for j in js:
        c = share_ok([r["geh"] for r in scored(cal) if r["junction"] == j])
        if j in val_js:
            v = share_ok([r["geh"] for r in scored(val) if r["junction"] == j])
            vt, vr = f"{v:.0%}", verdict(v)
        else:
            vt, vr = "no 12 May data", "—"
        L.append(f"| {j} | {c:.0%} | {verdict(c)} | {vt} | {vr} |")
    cc, vv = share_ok([r["geh"] for r in scored(cal)]), share_ok([r["geh"] for r in scored(val)])
    L += [
        f"| **Corridor** | **{cc:.0%}** | **{verdict(cc)}** | **{vv:.0%}** (J03–J08) | **{verdict(vv)}** |",
        "",
    ]

    L += [
        "## Gridlock",
        "",
        "| Window | Vehicles loaded | Still waiting to enter at the end | Share | Teleports |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in runs:
        ld, wt = r["vehicles"].get("loaded", 0), r["vehicles"].get("waiting", 0)
        L.append(
            f"| {hour_label(r['start_h'])[:2]}:00 + {r['hours']} h | {ld:,} | {wt:,} | {wt / max(1, ld):.0%} | {r['teleports']:,} |"
        )
    L += [
        f"| **Day** | **{loaded:,}** | **{waiting:,}** | **{waiting / max(1, loaded):.0%}** | **{tele:,}** |",
        "",
    ]
    if cont:
        L += [
            "### One continuous run (why the day is scored in windows)",
            "",
            (
                "The same network run continuously from 08:00: vehicles still waiting to enter at the end of each hour. "
                "The backlog never drains, so a continuous run measures the queue, not the network."
            ),
            "",
            "| Until | Waiting to enter |",
            "| --- | --- |",
            *[f"| {h['until']} | {h['waiting']:,} |" for h in cont["hours"]],
            "",
        ]

    L += [
        "## Hourly GEH<5 share (calibration, 11 May)",
        "",
        "| Hour | " + " | ".join(js) + " |",
        "| --- |" + " --- |" * len(js),
    ]
    for h in range(24):
        cells = []
        for j in js:
            vals = [r["geh"] for r in cal if r["junction"] == j and r["hour"] == h]
            cells.append(f"{share_ok(vals):.0%}" if vals else "—")
        L.append(
            f"| {hour_label(h)}{' (not scored)' if h < WARMUP_HOURS else ''} | " + " | ".join(cells) + " |"
        )
    L += [
        "",
        "## 15 worst movement-hours (calibration, 11 May)",
        "",
        "| Junction | Movement | Hour | Survey, May 2026 | SIM | GEH |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for r in sorted(scored(cal), key=lambda r: -r["geh"])[:15]:
        L.append(
            f"| {r['junction']} | {r['movement']} | {hour_label(r['hour'])} | {r['survey']:,.0f} | {r['sim']:,.0f} | {r['geh']:.1f} |"
        )
    L.append("")

    L += w1_sections(m, waiting / max(1, loaded), *_side_files())

    fit = demand_fit(build_dir, m)
    L += ["## Demand fit before simulation (routeSampler)", "",
          f"- Survey turning vehicles (11 May): **{m['survey_turn_counts']:,}**; routes written: **{fit['vehicles']:,}**",
          f"- Static route fit: {fit['static_geh']}", ""]  # fmt: skip
    L += [
        "## Counted flow per assumed lane (busiest hour, Survey, May 2026)",
        "",
        "| Approach | Lanes (sim) | Busiest hour | Vehicles/h | Per lane |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in lane_load(m, config.CALIBRATION_DATE)[:12]:
        L.append(
            f"| {row['approach']} | {row['lanes']} | {hour_label(row['hour'])} | {row['veh']:,.0f} | {row['per_lane']:,.0f} |"
        )
    L += [
        "",
        "## Timing plan used (ASSUMED)",
        "",
        "| Junction | Cycle (s) | Greens (s) |",
        "| --- | --- | --- |",
    ]
    for j, p in m["plans"]["demand2"].items():
        L.append(
            f"| {j} | {p['cycle_s']} | {', '.join(str(ph['duration_s']) for ph in p['phases'] if ph['kind'] == 'green')} |"
        )
    L += ["", "## Flags", "", *[f"- {f}" for f in m["flags"]], "",
          "## Why it fails, and what fixes it", "",
          ("- The network is a schematic straight line with ASSUMED 500 m spacing, lanes and timings; even the best search "
          "setting (one extra lane per direction) cannot carry the counted peak demand, so queues spill back and vehicles "
          "cannot enter."),
          ("- SUMO itself discharges queues at a realistic rate (see saturation flow), so the gap is geometry and capacity, "
          "not the traffic model."),
          ("- Next: verified junction coordinates (the OSM network is built automatically once the registry has them), "
          "measured lane counts and stopwatch timings (data/signal_timings.csv), then rerun this report. Nothing was tuned "
          "to force a pass, and 12 May was never used to choose."),
          "",
          "Input hashes: " + ", ".join(f"`{k}` {v}" for k, v in m["inputs"].items()), ""]  # fmt: skip
    out = config.REPORTS_DIR / "calibration.md"
    out.write_text("\n".join(L), encoding="utf-8")
    summary = {"calibration_share": cc, "validation_share": vv, "unserved_share": waiting / max(1, loaded), "teleports": tele,
               "method": f"{len(WINDOWS)} x 3-h windows, {WARMUP_MIN}-min warm-up"}  # fmt: skip
    (config.REPORTS_DIR / "calibration_day.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        f"[calibrate] day: calibration {cc:.0%} ({verdict(cc)}), validation {vv:.0%} ({verdict(vv)}), unserved {summary['unserved_share']:.0%}"
    )
    return out


def _side_files():
    r = config.REPORTS_DIR
    diag = (
        json.loads((r / "calibration_diagnostics.json").read_text())
        if (r / "calibration_diagnostics.json").exists()
        else None
    )
    trials = (r / "calibration_trials.csv").read_text() if (r / "calibration_trials.csv").exists() else None
    best = (
        json.loads((r / "calibration_best.json").read_text())
        if (r / "calibration_best.json").exists()
        else None
    )
    return diag, trials, best


def main() -> None:
    b = build("auto")
    t0 = time.monotonic()
    runs = run_day(b)
    write(b, runs, time.monotonic() - t0)


if __name__ == "__main__":
    main()
