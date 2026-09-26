"""uv run python -m ml.study --synthetic | --export study_export.json  -> reports/field_study.{md,json}"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from .analyse import analyse
from .synth import cohort

REPORTS = Path(__file__).resolve().parents[2] / "reports"
NAMES = {
    "stops": ("Stops per run", ""),
    "travelTimeS": ("Travel time J08→J03", " s"),
    "timeStoppedS": ("Time stopped", " s"),
}


def report(res: dict) -> str:
    sim = res["source"] == "SIM"
    L = [
        "# HariBatti — field study: advice ON vs OFF (W14)",
        "",
        f"> **{res['source']}** · {res['runs']} runs · generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC  ",
        "> A stop = below 5 km/h for at least 3 s. The first and last 200 m of every trace are removed before analysis.",
        "",
    ]
    if sim:
        L += ["**These are synthetic runs (SIM) that test the pipeline. They are not evidence**: the difference below comes",
              "from the simulation's own driver model (80% of drivers follow a GLOSA speed within 400 m of a signal), not from",
              "people. The real result needs the 20 GPS test drives with the app's Study mode.", ""]  # fmt: skip
    L += [
        "| Arm | Runs | Stops per run | Travel time (s) | Time stopped (s) | Mean speed (km/h) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for arm, label in (("advice", "Advice ON"), ("control", "Advice OFF")):
        a = res["byArm"][arm]
        L.append(
            f"| {label} | {a['runs']} | {a['stops']} | {a['travelTimeS']} | {a['timeStoppedS']} | {a['meanSpeedKmh']} |"
        )
    L += ["", "| Measure | ON − OFF | 95% CI (bootstrap) | Relative | Permutation p | Smallest detectable difference (80% power) |",
          "| --- | --- | --- | --- | --- | --- |"]  # fmt: skip
    for k, c in res["compare"].items():
        name, unit = NAMES[k]
        L.append(
            f"| {name} | {c['diff']}{unit} | {c['ci95'][0]} to {c['ci95'][1]}{unit} | {c['relative']}% | {c['pPermutation']} | {c['minDetectable']}{unit} |"
        )
    L += [""]
    for k, c in res["compare"].items():
        if c["crossesZero"]:
            L.append(f"- **{NAMES[k][0]}: the 95% CI crosses zero — no difference can be claimed.**")
        else:
            L.append(f"- {NAMES[k][0]}: the 95% CI excludes zero{' (in simulation only)' if sim else ''}.")
    L += ["", "## Limits", "",
          "- 20 runs detect only large effects (see the last column); runs by the same person are not independent, and",
          "  the bootstrap resamples runs, so CIs are somewhat too narrow if people differ a lot.",
          "- Junction positions and timings are ASSUMED until verified; the real study uses the live or stopwatch timings.",
          "- Advice ON/OFF is assigned by the server in blocks of two per participant, so arms stay balanced.",
          "", "Reproduce: `cd services/ml && uv run python -m ml.study --synthetic` (or `--export <file>` for real runs).", ""]  # fmt: skip
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--synthetic", action="store_true")
    g.add_argument("--export", type=Path)
    a = ap.parse_args()
    if a.synthetic:
        res = analyse(cohort(), "SIM")
    else:
        data = json.loads(a.export.read_text(encoding="utf-8"))
        res = analyse(data["runs"], data.get("source", "FIELD"))
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "field_study.json").write_text(
        json.dumps(
            {k: v for k, v in res.items() if k != "perRun"}
            | {"perRun": [{k: v for k, v in r.items() if k != "profile"} for r in res["perRun"]]},
            indent=2,
        )
        + "\n"
    )
    (REPORTS / "field_study.md").write_text(report(res), encoding="utf-8")
    print(json.dumps(res["byArm"]), json.dumps(res["compare"]))


if __name__ == "__main__":
    main()
