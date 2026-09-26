"""Import a police timing-plan sheet (CSV, Excel or a PDF table) as a PROPOSED signal_timings file.

Nothing is applied automatically: the output goes to data/signal_timings.proposed.csv with a list of
problems, and a person checks it before copying rows into data/signal_timings.csv (the source of truth).
Run: uv run python -m app.connectors.timing_import plan.pdf [--out data/signal_timings.proposed.csv]
"""

import csv
import re
from pathlib import Path
from typing import Any

from ..config import ROOT
from .file_drop import read_table

COLUMNS = ["junction_id", "date", "time_window", "phase_no", "approaches_served", "green_s", "amber_s", "all_red_s", "cycle_s", "signal_mode", "notes"]  # fmt: skip
# header spellings seen in police / vendor sheets -> our column
SYNONYMS = {
    "junction_id": ["junction id", "junction", "jn", "jn id", "site", "site id", "intersection"],
    "date": ["date", "effective date", "from date"],
    "time_window": ["time window", "period", "time", "plan period", "timing"],
    "phase_no": ["phase no", "phase", "stage", "stage no", "phase number"],
    "approaches_served": ["approaches served", "approach", "approaches", "movement", "movements", "arm"],
    "green_s": ["green s", "green", "green time", "green sec", "g"],
    "amber_s": ["amber s", "amber", "yellow", "amber time", "intergreen amber"],
    "all_red_s": ["all red s", "all red", "red clearance", "all-red", "ar"],
    "cycle_s": ["cycle s", "cycle", "cycle time", "cycle length"],
    "signal_mode": ["signal mode", "mode", "control mode", "type"],
    "notes": ["notes", "remarks", "remark", "comment"],
}  # fmt: skip
MODES = {"FIXED", "ACTUATED", "ADAPTIVE", "MANUAL", "FLASHING"}


def _norm(h: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(h or "").lower()).strip()


def header_map(headers: list[Any]) -> dict[str, str]:
    """Their header -> our column, by exact synonym match first, then by prefix."""
    out: dict[str, str] = {}
    for h in headers:
        n = _norm(h)
        for col, names in SYNONYMS.items():
            if col in out.values():
                continue
            if n in names or n == _norm(col) or any(n.startswith(x + " ") for x in names if len(x) > 2):
                out[str(h)] = col
                break
    return out


def pdf_rows(path: Path) -> list[dict[str, Any]]:
    """Tables from every page of a PDF (text PDFs; scanned images need OCR first)."""
    import pdfplumber

    rows: list[dict[str, Any]] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if len(table) < 2:
                    continue
                head = [str(h or "").strip() for h in table[0]]
                rows += [dict(zip(head, r, strict=False)) for r in table[1:]]
    return rows


def _num(v: Any) -> float | None:
    m = re.search(r"-?\d+(\.\d+)?", str(v or ""))
    return float(m.group()) if m else None


def propose(rows: list[dict[str, Any]], known: set[str]) -> tuple[list[dict[str, Any]], list[str]]:
    """Map raw rows to signal_timings rows and list every problem a reviewer must look at."""
    if not rows:
        return [], ["no table rows found"]
    hm = header_map(list(rows[0].keys()))
    missing = [c for c in ("junction_id", "phase_no", "green_s") if c not in hm.values()]
    if missing:
        return [], [
            f"could not find columns: {', '.join(missing)} (headers seen: {', '.join(map(str, rows[0].keys()))})"
        ]
    out, problems = [], []
    for i, raw in enumerate(rows, start=2):
        r = {col: raw.get(h) for h, col in hm.items()}
        jid = str(r.get("junction_id") or "").strip().upper()
        if not jid:
            continue
        m = re.fullmatch(r"J?0?(\d)", jid)
        jid = f"J0{m.group(1)}" if m else jid
        if jid not in known:
            problems.append(
                f"row {i}: junction '{jid}' is not in data/junction_registry.csv (not renamed or invented; fix by hand)"
            )
            continue
        g, a, ar, c = (
            _num(r.get("green_s")),
            _num(r.get("amber_s")),
            _num(r.get("all_red_s")),
            _num(r.get("cycle_s")),
        )
        if g is None or not 3 <= g <= 240:
            problems.append(f"row {i} ({jid}): green '{r.get('green_s')}' is missing or outside 3–240 s")
        if a is not None and not 2 <= a <= 6:
            problems.append(f"row {i} ({jid}): amber {a:g} s is outside the usual 2–6 s")
        mode = str(r.get("signal_mode") or "FIXED").strip().upper()
        if mode not in MODES:
            problems.append(f"row {i} ({jid}): unknown signal mode '{mode}'")
        out.append({
            "junction_id": jid, "date": str(r.get("date") or "").strip(), "time_window": str(r.get("time_window") or "").strip(),
            "phase_no": int(_num(r.get("phase_no")) or 0), "approaches_served": str(r.get("approaches_served") or "").strip(),
            "green_s": g if g is None else round(g), "amber_s": 3 if a is None else round(a), "all_red_s": 2 if ar is None else round(ar),
            "cycle_s": "" if c is None else round(c), "signal_mode": mode,
            "notes": ("IMPORTED – REVIEW; " + str(r.get("notes") or "").strip()).strip("; "),
        })  # fmt: skip
    # cycle check: greens + amber + all-red per junction/window should add up to the stated cycle
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in out:
        groups.setdefault((r["junction_id"], r["time_window"]), []).append(r)
    for (j, w), rs in groups.items():
        cyc = next((r["cycle_s"] for r in rs if r["cycle_s"] != ""), None)
        total = sum((r["green_s"] or 0) + r["amber_s"] + r["all_red_s"] for r in rs)
        if cyc and abs(total - cyc) > 2:
            problems.append(
                f"{j} {w or '(no window)'}: phases add up to {total} s but the cycle says {cyc} s"
            )
    return out, problems


def read_any(path: Path) -> list[dict[str, Any]]:
    return pdf_rows(path) if path.suffix.lower() == ".pdf" else read_table(path)


def known_junctions() -> set[str]:
    with (ROOT / "data/junction_registry.csv").open(newline="", encoding="utf-8") as f:
        return {r["junction_id"] for r in csv.DictReader(f)}


def write(rows: list[dict[str, Any]], out: Path) -> None:
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(
        description="Propose data/signal_timings rows from a police timing sheet (review before use)."
    )
    ap.add_argument("file", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "data/signal_timings.proposed.csv")
    a = ap.parse_args()
    rows, problems = propose(read_any(a.file), known_junctions())
    write(rows, a.out)
    print(f"[timing-import] {len(rows)} rows -> {a.out}")
    for p in problems:
        print(f"  CHECK: {p}")
    print("Nothing was applied. Review the file, then copy the rows you trust into data/signal_timings.csv.")


if __name__ == "__main__":
    main()
