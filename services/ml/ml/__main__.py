"""Command line: `uv run python -m ml report`.

Prints the v/c table (AM and PM peak, 11 May 2026) and the forecaster MAPE per junction, and
writes services/ml/reports/analytics.md with the same tables. Only aggregates are printed:
never raw survey rows.
"""

import sys
import warnings

from . import data
from .capacity import VC_FLAG_LIMIT, junction_timing, vc_table
from .forecast import evaluate

REPORT_DATE = "2026-05-11"


def _table(headers: list[str], rows: list[list]) -> list[str]:
    """Markdown table lines."""
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    out += ["| " + " | ".join("" if v is None else str(v) for v in r) + " |" for r in rows]
    return out


def _fmt(value: float | None, digits: int = 2) -> str:
    """Number with fixed decimals, or n/a."""
    return "n/a" if value is None else f"{value:.{digits}f}"


def vc_section() -> list[str]:
    """v/c tables as markdown lines (AM first, then PM)."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rows = vc_table(REPORT_DATE)
    lines = [f"## v/c per approach, peak hours of {REPORT_DATE} ({data.SURVEY_LABEL})", ""]
    lines.append(
        f"capacity = saturation flow x lanes x g / C; v/c > {VC_FLAG_LIMIT} is flagged. Under the assumed "
        "2-phase plan left turns run free, so the flow is S + R PCU/h. One fixed plan per junction "
        "(built from its PM-peak counts) is used for both peaks."
    )
    lines.append("")
    timings = {r["junction_id"]: junction_timing(r["junction_id"], REPORT_DATE) for r in rows}
    labels = sorted({t["label"] for t in timings.values()})
    lines.append("Timing: " + "; ".join(labels) + ".")
    lane_src = sorted({r["lanes_source"] for r in rows})
    if "ASSUMED" in lane_src:
        a = data.load_assumptions()["lanes"]
        lines.append(
            f"Lanes: ASSUMED from services/sim/assumptions.toml (main {a['main_road']}, "
            f"cross {a['cross_road']}) where the registry is blank."
        )
    lines += [f"Note: {w.message}" for w in caught]
    for period in ("AM", "PM"):
        part = [r for r in rows if r["period"] == period]
        if not part:
            continue
        lines += ["", f"### {period} peak", ""]
        lines += _table(
            ["Junction", "Approach", "Hour", "Flow PCU/h", "Lanes", "g/C (s)", "Capacity", "v/c", "Flag"],
            [
                [
                    r["junction_id"],
                    r["approach"],
                    r["hour_start"],
                    f"{r['flow_pcu_h']:,.0f}",
                    f"{r['lanes']} ({r['lanes_source']})",
                    f"{r['green_s']}/{r['cycle_s']}",
                    f"{r['capacity_pcu_h']:,.0f}",
                    _fmt(r["vc"]),
                    r["flag"],
                ]
                for r in part
            ],
        )
    over = [r for r in rows if r["flag"] == "over 0.9"]
    lines += ["", f"{len(over)} of {len(rows)} approach-peaks have v/c > {VC_FLAG_LIMIT}."]
    return lines


def forecast_section() -> list[str]:
    """Forecaster MAPE tables as markdown lines (or a clear message when tmc_clean is missing)."""
    lines = ["## 15-min demand forecast: train 11 May, test 12 May (J03-J08)", ""]
    try:
        ev = evaluate()
    except FileNotFoundError as e:
        return [*lines, f"Skipped: {e}"]
    lines.append(
        f"Target: {ev['target']} ({ev['data_label']}). Model: {ev['model']} with features "
        f"{', '.join(ev['features'])}. Baseline: seasonal naive (12 May slot = 11 May slot). "
        f"{ev['mape_note']} Train rows {ev['n_train']}, test rows {ev['n_test']}."
    )
    lines.append("")
    rows = [
        [j, _fmt(v["baseline_mape"]), _fmt(v["model_mape"]), v["n"], v["excluded"]]
        for j, v in ev["junctions"].items()
    ]
    pooled, total = ev["corridor"]["pooled"], ev["corridor"]["total_series"]
    rows.append(
        [
            "Corridor (all movement-slots)",
            _fmt(pooled["baseline_mape"]),
            _fmt(pooled["model_mape"]),
            pooled["n"],
            pooled["excluded"],
        ]
    )
    rows.append(
        ["Corridor total per slot", _fmt(total["baseline_mape"]), _fmt(total["model_mape"]), total["n"], 0]
    )
    lines += _table(["Junction", "Baseline MAPE %", "Model MAPE %", "Slots used", "Slots excluded"], rows)
    wins = sum(v["model_mape"] < v["baseline_mape"] for v in ev["junctions"].values())
    lines += [
        "",
        (
            f"The model beats the seasonal naive baseline at {wins} of {len(ev['junctions'])} junctions "
            "(movement level). Limitation: only one training day exists, so the model never sees a real "
            "'previous day' value while training (a neighbouring-slot stand-in is used), and two survey "
            "days are too few to judge day-to-day variation."
        ),
    ]
    return lines


def report() -> str:
    """Build the full markdown report, print it and save it to services/ml/reports/analytics.md."""
    lines = [
        "# HariBatti analytics report (P5a)",
        "",
        f"Counts: {data.SURVEY_LABEL} (aggregates only). Read-only analysis: nothing here controls a signal.",
        "",
        *vc_section(),
        "",
        *forecast_section(),
        "",
    ]
    text = "\n".join(lines)
    data.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (data.REPORTS_DIR / "analytics.md").write_text(text, encoding="utf-8")
    return text


def main(argv: list[str]) -> int:
    """Entry point. Only the `report` command exists."""
    if argv[:1] != ["report"]:
        print("usage: python -m ml report", file=sys.stderr)
        return 2
    print(report())
    print(f"\nWritten: {(data.REPORTS_DIR / 'analytics.md').relative_to(data.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
