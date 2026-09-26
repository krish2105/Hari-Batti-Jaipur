"""Compare every controller on held-out demand (12 May) and write services/ml/reports/controllers.json
and timespace.json. Everything is SIM on the calibrated schematic network with ASSUMED timing.

Window: 18:00-19:00 (PM peak) after a 15-min warm-up, plus a 15-min cool-down so trips that
started in the window can finish. Trips still running at the end are counted with the time they
had spent so far (never dropped), and vehicles still waiting to enter are reported as unserved.
Each controller runs with 5 SUMO seeds (and each trained PPO model counts separately), and we
report mean ± 95% confidence half-width (t-distribution).
Run: uv run --group rl python -m sim.opt.evaluate [--workers 6]
"""

import argparse
import json
import os
import statistics
import subprocess
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault("LIBSUMO_AS_TRACI", "1")

from scipy.stats import t as student_t

from ..build import load_manifest, state_string
from ..sumo_env import binary, sumolib
from .distil import distil, intergreen_states
from .greenwave import Junction, bandwidth, best_common_plan
from .networks import (
    CAL,
    CORRIDOR,
    ML_REPORTS,
    OPT_DIR,
    _moves,
    corridor_routes,
    cut_net,
    fixed_programs,
    junction_flows,
    links_on,
    stages,
    survey_seconds,
    write_json,
)  # fmt: skip

TRAIN_DATE, EVAL_DATE = "2026-05-11", "2026-05-12"
WARM, FROM, TO, END = "17:45", "18:00", "19:00", "19:15"
SEEDS = [1, 2, 3, 4, 5]
SPACING_M = 500  # ASSUMED, as in the schematic network
SPEED_KMH = 35  # progression speed for the green wave
EVAL_DIR = OPT_DIR / "eval"
MODELS = OPT_DIR / "models"
PERIODS = {
    "AM peak 08:00-11:00": ("08:00", 3),
    "Midday 12:00-15:00": ("12:00", 3),
    "PM peak 17:00-20:00": ("17:00", 3),
}

LABELS = {
    "even": ("Fixed time, even split 120 s (ASSUMED current)", "fixed"),
    "demand2": ("Webster, 2-phase with free left", "fixed"),
    "webster4": ("Webster, approach-wise (4 stages)", "fixed"),
    "greenwave": ("Webster 2-phase + green-wave offsets", "coordinated fixed"),
    "maxpressure": ("MaxPressure", "adaptive rule"),
    "ppo-single": ("PPO, single-junction agent", "reinforcement learning"),
    "ppo-corridor": ("PPO, corridor agent (neighbour pressure)", "reinforcement learning"),
    "ppo-distilled": ("Fixed plan distilled from the corridor PPO", "fixed (distilled)"),
}


# ---------------------------------------------------------------- measuring one run


def measure(tripinfo: Path, summary: Path) -> dict:
    t0, t1 = survey_seconds(FROM), survey_seconds(TO)
    all_trips = list(ET.parse(tripinfo).getroot().iter("tripinfo"))
    trips = [t for t in all_trips if t0 <= float(t.get("depart")) < t1]
    arrived = sum(t0 <= float(t.get("arrival", -1)) < t1 for t in all_trips)
    n = max(1, len(trips))
    delay = [float(t.get("departDelay", 0)) for t in trips]
    co2 = [
        float(e.get("CO2_abs", 0)) / 1000 for t in trips if (e := t.find("emissions")) is not None
    ]  # mg -> g
    halting, waiting_at_end = [], 0
    for s in ET.parse(summary).getroot().iter("step"):
        tt = float(s.get("time"))
        if t0 <= tt < t1:
            halting.append(float(s.get("halting", 0)))
        if abs(tt - t1) < 0.5:
            waiting_at_end = int(float(s.get("waiting", 0)))
    return {
        "trips": len(trips),
        "travelTimeS": sum(float(t.get("duration")) + d for t, d in zip(trips, delay, strict=True)) / n,
        "waitingTimeS": sum(float(t.get("waitingTime")) + d for t, d in zip(trips, delay, strict=True)) / n,
        "stops": sum(float(t.get("waitingCount")) for t in trips) / n,
        "queueVeh": sum(halting) / max(1, len(halting)),
        "throughputVeh": arrived,
        "co2PerTripG": sum(co2) / max(1, len(co2)),
        "unservedVeh": waiting_at_end,
    }


def _outputs(work: Path) -> tuple[list[str], Path, Path]:
    trip, summ = work / "tripinfo.xml", work / "summary.xml"
    opts = ["--tripinfo-output", str(trip), "--tripinfo-output.write-unfinished", "true", "--summary-output",
            str(summ), "--device.emissions.probability", "1"]  # fmt: skip
    return opts, trip, summ


def scope_inputs(scope: str, date: str) -> tuple[Path, Path, list[str]]:
    """(network, routes, junctions) for the corridor or one isolated junction."""
    if scope == "corridor":
        net = cut_net(CORRIDOR, "corridor")
        return net, corridor_routes(date, net.parent / f"routes-{date}.rou.xml"), list(CORRIDOR)
    net = cut_net([scope], scope)
    routes = net.parent / f"flows-{date}.rou.xml"
    if not routes.exists():
        junction_flows(scope, date, routes)
    return net, routes, [scope]


def run_fixed(scope: str, date: str, tls_add: Path, seed: int, work: Path) -> dict:
    net, routes, _ = scope_inputs(scope, date)
    opts, trip, summ = _outputs(work)
    cmd = [binary("sumo"), "-n", str(net), "-r", str(routes), "-a", f"{net.parent / 'vtypes.add.xml'},{tls_add}",
           "--begin", str(survey_seconds(WARM)), "--end", str(survey_seconds(END)), "--lateral-resolution", "0.8",
           "--no-step-log", "true", "--seed", str(seed), "--time-to-teleport", "300", "--no-warnings", "true", *opts]  # fmt: skip
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return measure(trip, summ)


def run_adaptive(scope: str, date: str, policy: str, model: str | None, seed: int, work: Path,
                 start: str = WARM, seconds: int | None = None, record: bool = False) -> dict:  # fmt: skip
    """MaxPressure or a trained PPO policy through the same sumo-rl mechanics."""
    from .envs import make_env, max_pressure_actions

    net, routes, _jids = scope_inputs(scope, date)
    opts, trip, summ = _outputs(work)
    secs = seconds or survey_seconds(END) - survey_seconds(WARM)
    corridor_obs = policy == "ppo-corridor"
    env = make_env(net, routes, [start], secs, corridor=corridor_obs, single_agent=False, sumo_seed=seed,
                   extra_cmd=" ".join(opts))  # fmt: skip
    ppo = None
    if model:
        from stable_baselines3 import PPO

        ppo = PPO.load(model, device="cpu")
    obs = env.reset()
    seq: dict[str, list[int]] = {j: [] for j in env.ts_ids}
    done = False
    while not done:
        if policy == "maxpressure":
            act = max_pressure_actions(env)
        else:
            act = {j: int(ppo.predict(o, deterministic=True)[0]) for j, o in obs.items()}
        obs, _r, dones, _i = env.step(act)
        if record:
            for j, ts in env.traffic_signals.items():
                seq[j].append(ts.green_phase)
        done = dones["__all__"]
    env.close()
    out = {} if record else measure(trip, summ)
    if record:
        out["stages"] = seq
    return out


# ---------------------------------------------------------------- plans written for fixed runs


def program_file(net_file: Path, jids: list[str], phases: dict[str, list[tuple[str, int]]], out: Path,
                 offsets: dict[str, int] | None = None) -> Path:  # fmt: skip
    m = load_manifest(CAL)
    parts = ["<additional>"]
    for j in jids:
        parts.append(
            f'  <tlLogic id="{m["tls_ids"][j]}" type="static" programID="haribatti" offset="{(offsets or {}).get(j, 0)}">'
        )
        parts += [f'    <phase duration="{d}" state="{s}"/>' for s, d in phases[j]]
        parts.append("  </tlLogic>")
    parts.append("</additional>")
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return out


def green_wave() -> dict:
    """Common cycle + bandwidth-maximising offsets on the corridor (demand2 green shares)."""
    m = load_manifest(CAL)
    plans = {}
    for j in CORRIDOR:
        g = [p["duration_s"] for p in m["plans"]["demand2"][j]["phases"] if p["kind"] == "green"]
        plans[j] = (m["plans"]["demand2"][j]["cycle_s"], g[0], g[1])
    inter = sum(p["duration_s"] for p in m["plans"]["demand2"][CORRIDOR[0]]["phases"] if p["kind"] != "green")
    v = SPEED_KMH / 3.6
    xs = {j: float(i * SPACING_M) for i, j in enumerate(CORRIDOR)}
    cycle, best = best_common_plan(plans, xs, inter, v)
    greens = {j.id: (int(j.green), cycle - inter - int(j.green)) for j in best}
    # the same cycle and greens with every offset 0 (today), for comparison
    zero = [Junction(j.id, j.x, j.green, 0.0) for j in best]
    bw = lambda js, d: bandwidth(js, cycle, v, d)
    return {
        "cycleS": cycle,
        "greens": greens,
        "offsets": {j.id: int(j.offset) for j in best},
        "bandwidthS": {"eastbound": bw(best, "east"), "westbound": bw(best, "west")},
        "bandwidthZeroOffsetsS": {"eastbound": bw(zero, "east"), "westbound": bw(zero, "west")},
        "junctions": [
            {"id": j.id, "x": j.x, "cycleS": cycle, "greenS": j.green, "offsetS": int(j.offset)} for j in best
        ],
    }


def greenwave_programs(net_file: Path, gw: dict, out: Path) -> Path:
    m = load_manifest(CAL)
    net = sumolib.net.readNet(str(net_file), withPrograms=True)
    phases = {}
    for j in CORRIDOR:
        links, n = links_on(net, m, j)
        main, cross = gw["greens"][j]
        greens = iter([main, cross])
        phases[j] = [(state_string(_moves(p["moves"]), links, n), next(greens) if p["kind"] == "green" else p["duration_s"])
                     for p in m["plans"]["demand2"][j]["phases"]]  # fmt: skip
    return program_file(net_file, CORRIDOR, phases, out, gw["offsets"])


def distilled_programs(net_file: Path, plan: dict, out: Path) -> Path:
    """Fixed programs from a distilled plan {junction: {"stages": [(stage, green s)]}}."""
    m = load_manifest(CAL)
    net = sumolib.net.readNet(str(net_file), withPrograms=True)
    phases = {}
    for j in CORRIDOR:
        links, n = links_on(net, m, j)
        states = [state_string(s, links, n) for s in stages(m, j)]
        seq = plan[j]["stages"]
        ph = []
        for k, (stage, green) in enumerate(seq):
            nxt = seq[(k + 1) % len(seq)][0]
            amber, allred = intergreen_states(states[stage], states[nxt])
            ph += [(states[stage], green), (amber, 3), (allred, 2)]
        phases[j] = ph
    return program_file(net_file, CORRIDOR, phases, out)


def stage_labels(jid: str) -> list[str]:
    m = load_manifest(CAL)
    name = {v["side"]: k for k, v in m["approaches"][jid].items()}
    return ["Main road, straight + right (free left)", "Cross road, straight + right (free left)",
            f"{name['W']} arm only", f"{name['N']} arm only", f"{name['E']} arm only", f"{name['S']} arm only"]  # fmt: skip


# ---------------------------------------------------------------- tasks


def _task(t: dict) -> dict:
    """One run (cached on disk so an interrupted evaluation resumes)."""
    work = EVAL_DIR / t["key"]
    done = work / "result.json"
    if done.exists():
        return json.loads(done.read_text())
    work.mkdir(parents=True, exist_ok=True)
    if t["kind"] == "fixed":
        r = run_fixed(t["scope"], t["date"], Path(t["tls"]), t["seed"], work)
    else:
        r = run_adaptive(t["scope"], t["date"], t["policy"], t.get("model"), t["seed"], work,
                         start=t.get("start", WARM), seconds=t.get("seconds"), record=t.get("record", False))  # fmt: skip
    for f in ("tripinfo.xml", "summary.xml"):
        (work / f).unlink(missing_ok=True)  # large; the numbers are kept in result.json
    r = {**r, **{k: t[k] for k in ("controller", "scope", "seed")}, "model": t.get("model")}
    done.write_text(json.dumps(r))
    print(
        f"[eval] {t['key']}: " + ", ".join(f"{k}={v:.1f}" for k, v in r.items() if isinstance(v, float)),
        flush=True,
    )
    return r


def task(key: str, controller: str, scope: str, seed: int, **extra) -> dict:
    """One evaluation run: fixed when a signal program file (tls=...) is given, else adaptive."""
    kind = "fixed" if "tls" in extra else "adaptive"
    date = extra.pop("date", EVAL_DATE)
    return {
        "key": key,
        "kind": kind,
        "controller": controller,
        "scope": scope,
        "seed": seed,
        "date": date,
        **extra,
    }


def ci(values: list[float]) -> dict:
    n = len(values)
    mean = statistics.fmean(values)
    if n < 2:
        return {"mean": round(mean, 2), "ci95": None}
    half = student_t.ppf(0.975, n - 1) * statistics.stdev(values) / n**0.5
    return {"mean": round(mean, 2), "ci95": round(half, 2)}


def summarise(rows: list[dict], controller: str) -> dict:
    mine = [r for r in rows if r["controller"] == controller]
    label, kind = LABELS[controller]
    keys = ("travelTimeS", "waitingTimeS", "stops", "queueVeh", "throughputVeh", "co2PerTripG", "unservedVeh")
    return {
        "id": controller,
        "label": label,
        "kind": kind,
        "runs": len(mine),
        **{k: ci([r[k] for r in mine]) for k in keys},
    }


def models(kind: str) -> list[str]:
    return sorted(str(p) for p in MODELS.glob(f"{kind}-seed*.zip") if "seed99" not in p.name)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--skip-isolated", action="store_true")
    a = ap.parse_args()
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    corr_net = cut_net(CORRIDOR, "corridor")
    for d in (TRAIN_DATE, EVAL_DATE):
        corridor_routes(d, corr_net.parent / f"routes-{d}.rou.xml")

    # fixed programs on the corridor, including the green wave
    tls = {
        p: fixed_programs(corr_net, CORRIDOR, p, corr_net.parent / f"fixed-{p}.add.xml")
        for p in ("even", "demand2", "webster4")
    }
    gw = green_wave()
    tls["greenwave"] = greenwave_programs(corr_net, gw, corr_net.parent / "fixed-greenwave.add.xml")
    single, corridor = models("single"), models("corridor")

    # distil the corridor PPO per period on the TRAINING day (11 May)
    distilled: dict[str, dict] = {}
    if corridor:
        rec = [task(key=f"record-{Path(corridor[0]).stem}-{p[:2]}", controller="record", scope="corridor",
                    date=TRAIN_DATE, policy="ppo-corridor", model=corridor[0], seed=11, start=s, seconds=h * 3600, record=True)
               for p, (s, h) in PERIODS.items()]  # fmt: skip
        with ProcessPoolExecutor(a.workers) as pool:
            recs = list(pool.map(_task, rec))
        from .envs import DELTA_S, MIN_GREEN_S

        for (period, _), r in zip(PERIODS.items(), recs, strict=True):
            distilled[period] = {}
            for j in CORRIDOR:
                cyc, greens = distil(r["stages"][j], DELTA_S, 5, MIN_GREEN_S)
                labels = stage_labels(j)
                distilled[period][j] = {"cycleS": cyc, "stages": [[s, g] for s, g in greens],
                                        "labels": [labels[s] for s, _ in greens]}  # fmt: skip
        tls["ppo-distilled"] = distilled_programs(
            corr_net, distilled["PM peak 17:00-20:00"], corr_net.parent / "fixed-ppo-distilled.add.xml"
        )

    tasks = []
    for c, path in tls.items():
        tasks += [
            task(
                key=f"corridor-{c}-s{s}",
                controller=c,
                scope="corridor",
                date=EVAL_DATE,
                tls=str(path),
                seed=s,
            )
            for s in SEEDS
        ]
    tasks += [task(key=f"corridor-maxpressure-s{s}", controller="maxpressure", scope="corridor",
                   date=EVAL_DATE, policy="maxpressure", seed=s) for s in SEEDS]  # fmt: skip
    for pol, paths in (("ppo-single", single), ("ppo-corridor", corridor)):
        for mdl in paths:
            tasks += [task(key=f"corridor-{pol}-{Path(mdl).stem}-s{s}", controller=pol, scope="corridor",
                           date=EVAL_DATE, policy=pol, model=mdl, seed=s) for s in SEEDS]  # fmt: skip
    iso_tasks = []
    if not a.skip_isolated:
        for j in CORRIDOR:
            net_j, _, _ = scope_inputs(j, EVAL_DATE)
            for p in ("even", "demand2", "webster4"):
                f = fixed_programs(net_j, [j], p, net_j.parent / f"fixed-{p}.add.xml")
                iso_tasks += [
                    task(
                        key=f"{j}-{p}-s{s}",
                        controller=p,
                        scope=j,
                        date=EVAL_DATE,
                        tls=str(f),
                        seed=s,
                    )
                    for s in SEEDS
                ]
            iso_tasks += [task(key=f"{j}-maxpressure-s{s}", controller="maxpressure", scope=j,
                               date=EVAL_DATE, policy="maxpressure", seed=s) for s in SEEDS]  # fmt: skip
            for mdl in single:
                iso_tasks += [task(key=f"{j}-ppo-single-{Path(mdl).stem}-s{s}", controller="ppo-single",
                                   scope=j, date=EVAL_DATE, policy="ppo-single", model=mdl, seed=s) for s in SEEDS]  # fmt: skip
    with ProcessPoolExecutor(a.workers) as pool:
        rows = list(pool.map(_task, tasks + iso_tasks))

    corr_rows = [r for r in rows if r["scope"] == "corridor"]
    order = [c for c in LABELS if any(r["controller"] == c for r in corr_rows)]
    iso = {}
    for j in CORRIDOR:
        jr = [r for r in rows if r["scope"] == j]
        iso[j] = [summarise(jr, c) for c in LABELS if any(r["controller"] == c for r in jr)]
    meta_models = {
        Path(p).stem: json.loads(Path(p).with_suffix(".json").read_text()) for p in single + corridor
    }
    manifest = load_manifest(CAL)
    result = {
        "source": "SIM",
        "network": f"{manifest['geometry_label']} · calibrated build cut to the J03-J08 corridor · ASSUMED timing",
        "trainDay": TRAIN_DATE,
        "evalDay": EVAL_DATE,
        "window": f"{FROM}-{TO} after a 15-min warm-up (+15-min cool-down)",
        "seeds": SEEDS,
        "controllers": [summarise(corr_rows, c) for c in order],
        "isolated": iso,
        "distilled": [{"period": p, "junctions": v} for p, v in distilled.items()],
        "models": meta_models,
        "note": "SIM on a schematic, partly calibrated network (corridor GEH<5 about 47%): use the ranking, not the "
                "absolute seconds. Recommendations only - nothing is applied to a real signal.",
    }  # fmt: skip
    write_json(ML_REPORTS / "controllers.json", result)
    write_json(ML_REPORTS / "timespace.json", {
        "source": "SIM", "plan": "Webster 2-phase, common cycle", "speedKmh": SPEED_KMH, "spacingM": SPACING_M,
        "spacingSource": "ASSUMED", "cycleS": gw["cycleS"], "bandwidthS": gw["bandwidthS"],
        "bandwidthZeroOffsetsS": gw["bandwidthZeroOffsetsS"], "junctions": gw["junctions"],
        "note": f"Offsets maximise the green band both ways at {SPEED_KMH} km/h (common cycle {gw['cycleS']} s).",
    })  # fmt: skip
    print(f"[eval] wrote {ML_REPORTS / 'controllers.json'} and timespace.json", flush=True)


if __name__ == "__main__":
    main()
