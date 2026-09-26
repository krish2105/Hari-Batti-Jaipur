"""Write services/ml/reports/optimisation.md from controllers.json and timespace.json (all SIM).

Run after `python -m sim.opt.evaluate`: uv run python -m sim.opt.report
"""

import json
from datetime import UTC, datetime

from .. import config
from .networks import ML_REPORTS


def _m(x: dict, digits: int = 1) -> str:
    """mean ± 95% CI half-width."""
    if x["ci95"] is None:
        return f"{x['mean']:,.{digits}f}"
    return f"{x['mean']:,.{digits}f} ± {x['ci95']:,.{digits}f}"


def _pct(new: float, old: float) -> str:
    return "—" if not old else f"{100 * (new - old) / old:+.0f}%"


def build() -> str:
    c = json.loads((ML_REPORTS / "controllers.json").read_text(encoding="utf-8"))
    ts = json.loads((ML_REPORTS / "timespace.json").read_text(encoding="utf-8"))
    rows = c["controllers"]
    base = next((r for r in rows if r["id"] == "even"), rows[0])
    best = min(rows, key=lambda r: r["travelTimeS"]["mean"])
    L = [
        "# HariBatti — signal-timing optimisation (W2)",
        "",
        f"> **SIM** · {c['network']}  ",
        f"> Trained on {c['trainDay']} demand, evaluated on **{c['evalDay']}** demand (a day no controller saw) · "
        f"{c['window']} · SUMO seeds {', '.join(map(str, c['seeds']))} · mean ± 95% confidence half-width  ",
        f"> Generated {datetime.now(UTC).astimezone(config.IST):%Y-%m-%d %H:%M} IST",
        "",
        "Recommendations only: HariBatti never sends anything to a signal. An officer decides and applies any "
        "change in the real ITMS. The network is the schematic digital twin, calibrated only partly "
        "(corridor GEH<5 about 47%, see services/sim/reports/calibration.md), with ASSUMED lanes and timings — "
        "read the **ranking**, not the absolute seconds.",
        "",
        "## Corridor J03–J08, PM peak",
        "",
        "| Controller | Kind | Runs | Travel time (s) | Waiting (s) | Stops | Queue (veh) | Throughput (veh/h) "
        "| CO₂ per trip (g) | Unserved (veh) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        L.append(
            f"| {r['label']} | {r['kind']} | {r['runs']} | {_m(r['travelTimeS'])} | {_m(r['waitingTimeS'])} "
            f"| {_m(r['stops'], 2)} | {_m(r['queueVeh'], 0)} | {_m(r['throughputVeh'], 0)} "
            f"| {_m(r['co2PerTripG'], 0)} | {_m(r['unservedVeh'], 0)} |"
        )
    L += [
        "",
        f"Travel time includes time spent waiting to enter the network; trips still running at the end are "
        f"counted, not dropped. Lowest mean travel time: **{best['label']}** "
        f"({_pct(best['travelTimeS']['mean'], base['travelTimeS']['mean'])} vs {base['label']}).",
        "",
    ]
    if c.get("isolated"):
        L += [
            "## Single junctions in isolation (same held-out day and window)",
            "",
            "Each junction alone with its own surveyed turning counts. Mean travel time (s) ± 95% CI.",
            "",
        ]
        ctrls = [r["id"] for r in next(iter(c["isolated"].values()))]
        labels = {r["id"]: r["label"] for v in c["isolated"].values() for r in v}
        L.append("| Junction | " + " | ".join(labels[k] for k in ctrls) + " |")
        L.append("| --- |" + " --- |" * len(ctrls))
        for j, rs in c["isolated"].items():
            by = {r["id"]: r for r in rs}
            L.append(f"| {j} | " + " | ".join(_m(by[k]["travelTimeS"]) if k in by else "—" for k in ctrls) + " |")
        L.append("")
    if c.get("distilled"):
        L += [
            "## A plan an officer can key in (distilled from the corridor PPO agent)",
            "",
            "The agent's stage choices on the training day, turned into one fixed plan per time of day: "
            "stages used at least 5% of the time, cycle from how often the main stage came back, greens in "
            "proportion to the time held. Amber 3 s + all-red 2 s after every stage. SIM, recommendation only.",
            "",
        ]
        for d in c["distilled"]:
            L += [f"### {d['period']}", "", "| Junction | Cycle (s) | Stages (green s) |", "| --- | --- | --- |"]
            for j, p in d["junctions"].items():
                stages = "; ".join(f"{lab} {g}" for lab, (_s, g) in zip(p["labels"], p["stages"], strict=True))
                L.append(f"| {j} | {p['cycleS']} | {stages} |")
            L.append("")
    L += [
        "## Green wave (coordinated offsets)",
        "",
        f"Common cycle **{ts['cycleS']} s** (Webster 2-phase green shares kept), progression speed "
        f"{ts['speedKmh']} km/h, {ts['spacingSource']} spacing {ts['spacingM']} m. Offsets = when each junction's "
        "main-road green starts, in seconds into the cycle (same meaning as the dashboard time-space diagram).",
        "",
        "| Junction | Distance from J08 (m) | Main green (s) | Offset (s) |",
        "| --- | --- | --- | --- |",
    ]
    L += [f"| {j['id']} | {j['x']:,.0f} | {j['greenS']:.0f} | {j['offsetS']} |" for j in ts["junctions"]]
    L += [
        "",
        f"Green band: **{ts['bandwidthS']['eastbound']:.1f} s eastbound, {ts['bandwidthS']['westbound']:.1f} s "
        f"westbound** per cycle, versus {ts['bandwidthZeroOffsetsS']['eastbound']:.1f} s / "
        f"{ts['bandwidthZeroOffsetsS']['westbound']:.1f} s with every offset 0 (today's assumption). "
        "The time-space diagram is on the dashboard (Plan Studio → Optimised).",
        "",
        "## How it was done",
        "",
        "- **Fixed plans** (even split, Webster 2-phase, Webster approach-wise) come from the simulator build; "
        "the green wave uses the Webster 2-phase greens rescaled to one common cycle.",
        "- **MaxPressure** (Varaiya 2013) and **PPO** choose one of six stages every 6 s with a 10-s minimum "
        "green and 5 s of amber between stages, through the same sumo-rl mechanics.",
        "- **PPO** (stable-baselines3, MIT) with sumo-rl (MIT): reward = intersection pressure "
        "(vehicles leaving − vehicles approaching); observation = stage, min-green flag, per-lane queue and "
        "density in and out; the corridor agent also sees its neighbours' pressure (PressLight-style) and shares "
        "one policy across the six junctions.",
    ]
    for name, m in c.get("models", {}).items():
        L.append(
            f"- `{name}`: {m['steps']:,} steps on {m['train_date']}, "
            f"{m['wall_s'] // 60} min on a laptop CPU, network {m['net_arch']}"
        )
    L += [
        "",
        "## Honest limitations",
        "",
        "- Schematic geometry, ASSUMED 500 m spacing, lanes and timings; the twin reproduces only about half of "
        "the surveyed movement-hours (GEH<5), and the PM peak is oversaturated, so every controller leaves a "
        "queue. Differences between controllers matter more than the absolute seconds.",
        "- Only two survey days exist: agents train on 11 May and are tested on 12 May, which is a similar weekday.",
        "- Adaptive controllers need live detection (cameras or loops) that the pilot junctions do not have yet; "
        "the distilled fixed plan and the green-wave offsets are what could be tried first.",
        "- Amber + all-red is lumped into 5 s of amber for the adaptive controllers (sumo-rl has no all-red).",
        "",
        "Reproduce: `cd services/sim && uv run --group rl python -m sim.opt.train single --seed 0` (and "
        "`corridor`), then `uv run --group rl python -m sim.opt.evaluate` and `uv run python -m sim.opt.report`.",
        "",
    ]
    return "\n".join(L)


def main() -> None:
    out = ML_REPORTS / "optimisation.md"
    out.write_text(build(), encoding="utf-8")
    print(f"[report] wrote {out.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
