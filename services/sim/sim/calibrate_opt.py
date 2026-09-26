"""W1 automatic calibration with Optuna (Bayesian optimisation, TPE sampler).

Searches ONLY physically bounded parameters (P7):
  lanes on the main road 2-4 and cross roads 1-3 (the assumption is 3 / 2, +-1), driver
  headway tau 0.8-1.3 s, two-wheeler lateral gap 0.1-0.5 m, speed factor 0.9-1.15,
  lane use (netconvert default or dedicated right-turn lane).
Objective: maximise the share of movement-hours with GEH < 5 on 11 May (calibration windows).
12 May (validation) is computed and logged for every trial but NEVER used to choose.
Every trial is logged to services/sim/reports/calibration_trials.csv.
Run: uv run python -m sim.calibrate_opt --trials 30 --jobs 3
"""

import argparse
import csv
import json
import shutil
import time

import optuna

from . import config
from .build import build
from .evaluate import evaluate

BASE = "v1-nomid"  # midblock stubs off (no survey basis); its fitted routes are reused
LOG = config.REPORTS_DIR / "calibration_trials.csv"
FIELDS = [
    "trial",
    "main_lanes",
    "cross_lanes",
    "tau_s",
    "two_wheeler_min_gap_lat_m",
    "speed_factor",
    "turn_lanes",
    "calibration_geh_share",
    "validation_geh_share",
    "unserved_share",
    "teleports",
    "runtime_s",
]


def overrides_for(params: dict) -> dict:
    return {
        "network": {"midblock_access": False, "turn_lanes": params["turn_lanes"]},
        "lanes": {"main_road": params["main_lanes"], "cross_road": params["cross_lanes"]},
        "vehicles": {"tau_s": params["tau_s"], "speed_factor": params["speed_factor"], "speed_dev": 0.1},
        "sublane": {"two_wheeler_min_gap_lat_m": params["two_wheeler_min_gap_lat_m"]},
    }


def objective(trial: optuna.Trial) -> float:
    params = {
        "main_lanes": trial.suggest_int("main_lanes", 2, 4),
        "cross_lanes": trial.suggest_int("cross_lanes", 1, 3),
        "tau_s": trial.suggest_float("tau_s", 0.8, 1.3),
        "two_wheeler_min_gap_lat_m": trial.suggest_float("two_wheeler_min_gap_lat_m", 0.1, 0.5),
        "speed_factor": trial.suggest_float("speed_factor", 0.9, 1.15),
        "turn_lanes": trial.suggest_categorical("turn_lanes", ["auto", "dedicated_right"]),
    }
    name = f"opt-{trial.number:03d}"
    t0 = time.monotonic()
    out = build(
        "schematic",
        name=name,
        overrides=overrides_for(params),
        routes_from=config.BUILD_DIR / f"schematic-{BASE}",
    )
    r = evaluate(out)
    row = {
        "trial": trial.number,
        **params,
        "calibration_geh_share": round(r["calibration"]["corridor"], 4),
        "validation_geh_share": round(r["validation"]["corridor"], 4),
        "unserved_share": round(r["unserved_share"], 4),
        "teleports": r["teleports"],
        "runtime_s": round(time.monotonic() - t0),
    }
    trial.set_user_attr("validation_geh_share", row["validation_geh_share"])  # logged, never optimised
    trial.set_user_attr("unserved_share", row["unserved_share"])
    new = not LOG.exists()
    with LOG.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)
    shutil.rmtree(out, ignore_errors=True)  # keep the disk clean; the best is rebuilt at the end
    print(
        f"[opt] trial {trial.number}: cal {row['calibration_geh_share']:.0%} val {row['validation_geh_share']:.0%} "
        f"unserved {row['unserved_share']:.0%} {params}",
        flush=True,
    )
    return r["calibration"]["corridor"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument(
        "--fail-stale",
        action="store_true",
        help="mark trials left RUNNING by an interrupted earlier run as FAIL (only when no other run is active)",
    )
    args = ap.parse_args()
    config.REPORTS_DIR.mkdir(exist_ok=True)
    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=42),
        study_name="w1-calibration",
        storage=f"sqlite:///{config.BUILD_DIR / 'optuna.db'}",
        load_if_exists=True,
    )
    # Resuming: trials interrupted by a stopped run stay RUNNING in the sqlite storage forever.
    if args.fail_stale:
        for t in study.get_trials(deepcopy=False, states=(optuna.trial.TrialState.RUNNING,)):
            study._storage.set_trial_state_values(t._trial_id, optuna.trial.TrialState.FAIL)
            print(f"[opt] marked interrupted trial {t.number} as FAIL", flush=True)
    # start from the assumption and the best diagnostic variant so TPE has sensible anchors
    study.enqueue_trial(
        {
            "main_lanes": 3,
            "cross_lanes": 2,
            "tau_s": 1.0,
            "two_wheeler_min_gap_lat_m": 0.3,
            "speed_factor": 1.0,
            "turn_lanes": "auto",
        },
        skip_if_exists=True,  # a resumed study must not re-run the anchors
    )
    study.enqueue_trial(
        {
            "main_lanes": 4,
            "cross_lanes": 3,
            "tau_s": 1.0,
            "two_wheeler_min_gap_lat_m": 0.3,
            "speed_factor": 1.0,
            "turn_lanes": "auto",
        },
        skip_if_exists=True,  # a resumed study must not re-run the anchors
    )
    study.optimize(objective, n_trials=args.trials, n_jobs=args.jobs)
    best = study.best_trial
    (config.REPORTS_DIR / "calibration_best.json").write_text(
        json.dumps(
            {
                "trial": best.number,
                "params": best.params,
                "calibration_geh_share": best.value,
                "validation_geh_share": best.user_attrs.get("validation_geh_share"),
                "unserved_share": best.user_attrs.get("unserved_share"),
                "trials": len(study.trials),
                "objective": "share of movement-hours GEH<5 on 11 May, windows 09-10, 13-14, 18-19",
            },
            indent=2,
        )
    )
    print(f"[opt] best trial {best.number}: {best.value:.0%} {best.params}", flush=True)


if __name__ == "__main__":
    main()
