"""HariBatti — process classified 24-h Turning Movement Count (TMC) surveys.

Input : data/raw/tmc/<folder>/*.xlsx   (Summary + V_1..V_12 sheets, 96 x 15-min rows, 08:00 -> 08:00)
Output: data/processed/
  tmc_clean.csv              one row per junction x day x movement x 15-min slot (deduplicated)
  junction_day_summary.csv   daily totals, composition, AM/PM peak hour (PCU/hr) and peak-hour factor
  pm_peak_approach_turns.csv PCU/hr by approach and turn (L/S/R) in each junction's PM peak hour
  hourly_profile_pcu.csv     hourly PCU per junction-day (for charts and simulator demand)

Run: uv run --with pandas --with openpyxl python scripts/process_tmc.py
"""
import glob, re
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data/raw/tmc", ROOT / "data/processed"

CLASS_COLS = ["car_taxi_auto_pickup", "two_wheeler", "tractor_lcv_minibus", "axle_truck_bus",
              "truck_trailer_mav", "total_fast", "cycle", "cycle_rickshaw", "hand_cart",
              "horse_drawn", "bullock_cart", "total_slow", "total_veh", "total_pcu"]
FAST = CLASS_COLS[:5]
SLOW = ["cycle", "cycle_rickshaw", "hand_cart", "horse_drawn", "bullock_cart"]

# Canonical junctions. DAY1_8J files 3-8 are byte-for-byte the same counts as INT_11-05-2026 01-06,
# so J03-J08 use the INT files (which also have a second day, 12-05-2026).
REGISTRY = [
    ("J01", "SFS RIICO Junction",   "1 SFS RIICO",   None),
    ("J02", "SFS Agrawal Junction", "2 SFS Agrawal", None),
    ("J03", "Jansunvai Junction",   "01_TMC",        "TMC-01"),
    ("J04", "Vijay Path Junction",  "02_TMC",        "TMC-02"),
    ("J05", "Patel Marg Junction",  "03_TMC",        "TMC-03"),
    ("J06", "VT Road Junction",     "04_TMC",        "TMC-04"),
    ("J07", "Rajat Path Junction",  "05_TMC",        "TMC-05"),
    ("J08", "Bhrigu Path Junction", "06_TMC",        "TMC-06"),
]


def parse_workbook(path: Path) -> list[dict]:
    """Read one TMC workbook into tidy rows (one per movement x 15-min slot)."""
    wb = load_workbook(path, read_only=True, data_only=True)
    s = list(wb["Summary"].iter_rows(max_row=12, max_col=12, values_only=True))
    date, day = s[0][8], s[1][8]
    # Approach table: 'Approach' header, then 4 rows of [from, left-to, straight-to, right-to]
    i = next(k for k, r in enumerate(s) if r[0] == "Approach")
    turn_of = {}
    for r in s[i + 1:i + 5]:
        if r[0]:
            for turn, to in zip(("L", "S", "R"), r[1:4]):
                turn_of[(str(r[0]).strip().upper(), str(to).strip().upper())] = turn
    rows = []
    for name in wb.sheetnames:
        m = re.fullmatch(r"V_(\d+)", name)
        if not m:
            continue
        ws = list(wb[name].iter_rows(max_row=110, max_col=15, values_only=True))
        frm, to = str(ws[3][1]).strip(), str(ws[3][4]).strip()
        slot = 0
        for r in ws[5:]:
            t = r[0].replace(" ", "") if isinstance(r[0], str) else ""
            if not re.fullmatch(r"\d{4}-\d{4}", t) or slot >= 96:   # stop before hourly roll-ups
                continue
            rec = dict(survey_date=pd.Timestamp(date).date(), day=day, source_file=path.name,
                       movement=int(m.group(1)), from_approach=frm, to_approach=to,
                       turn=turn_of.get((frm.upper(), to.upper()), "?"),
                       slot=slot, start=f"{t[:2]}:{t[2:4]}")
            rec.update({c: (v if isinstance(v, (int, float)) else 0) for c, v in zip(CLASS_COLS, r[1:15])})
            rows.append(rec)
            slot += 1
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(RAW.glob("*/*.xlsx"))
    parts = []
    for jid, name, prefix, code in REGISTRY:
        for f in [f for f in files if f.name.startswith(prefix)]:
            df = pd.DataFrame(parse_workbook(f))
            df.insert(0, "junction_id", jid); df.insert(1, "junction_name", name); df.insert(2, "tmc_code", code)
            parts.append(df)
    c = pd.concat(parts, ignore_index=True)

    # Data fix: the survey's own 'Total Slow' column misses some slow vehicles -> recompute from parts.
    c["total_slow_reported"] = c["total_slow"]
    c["total_slow"] = c[SLOW].sum(axis=1)
    c["total_veh"] = c["total_fast"] + c["total_slow"]
    assert (c[FAST].sum(axis=1) == c["total_fast"]).all(), "fast-vehicle columns do not add up"
    c.to_csv(OUT / "tmc_clean.csv", index=False)

    # Daily totals + composition
    jd = c.groupby(["junction_id", "junction_name", "survey_date"]).agg(
        total_veh=("total_veh", "sum"), total_pcu=("total_pcu", "sum"),
        two_wheeler=("two_wheeler", "sum"), car_auto=("car_taxi_auto_pickup", "sum")).reset_index()
    jd["two_wheeler_pct"] = (jd.two_wheeler / jd.total_veh * 100).round(1)
    jd["car_auto_pct"] = (jd.car_auto / jd.total_veh * 100).round(1)

    # Peak hours = highest rolling 4 x 15-min PCU; PHF = hour PCU / (4 x busiest 15-min)
    s = c.groupby(["junction_id", "survey_date", "slot", "start"]).total_pcu.sum().reset_index()
    peaks = []
    for (j, dt), g in s.groupby(["junction_id", "survey_date"]):
        g = g.sort_values("slot").reset_index(drop=True)
        roll = g.total_pcu.rolling(4).sum()

        def best(lo, hi):   # lo/hi = index of the window's LAST slot
            w = roll[(g.slot >= lo) & (g.slot <= hi)]
            k = w.idxmax()
            return g.start[k - 3], w.max(), round(w.max() / (4 * g.total_pcu[k - 3:k + 1].max()), 2), int(g.slot[k - 3])
        am, pm = best(3, 19), best(36, 55)   # AM windows starting 08:00-12:00, PM 17:00-21:00
        peaks.append(dict(junction_id=j, survey_date=dt, am_peak_start=am[0], am_peak_pcu_hr=am[1], am_phf=am[2],
                          pm_peak_start=pm[0], pm_peak_pcu_hr=pm[1], pm_phf=pm[2], _pm_slot=pm[3]))
    pk = pd.DataFrame(peaks)
    jd.merge(pk.drop(columns="_pm_slot"), on=["junction_id", "survey_date"]).to_csv(OUT / "junction_day_summary.csv", index=False)

    # Approach x turn in the PM peak hour
    rows = []
    for _, r in pk.iterrows():
        g = c[(c.junction_id == r.junction_id) & (c.survey_date == r.survey_date) & c.slot.between(r._pm_slot, r._pm_slot + 3)]
        t = g.pivot_table(index="from_approach", columns="turn", values="total_pcu", aggfunc="sum", fill_value=0).reset_index()
        t.insert(0, "survey_date", r.survey_date); t.insert(0, "junction_id", r.junction_id)
        rows.append(t)
    ap = pd.concat(rows, ignore_index=True).fillna(0)
    ap["approach_pcu_hr"] = ap[[x for x in ("L", "S", "R") if x in ap]].sum(axis=1)
    ap.to_csv(OUT / "pm_peak_approach_turns.csv", index=False)

    # Hourly profile
    c["hour"] = c.start.str[:2]
    c.groupby(["junction_id", "survey_date", "hour"], sort=False).total_pcu.sum().reset_index() \
     .to_csv(OUT / "hourly_profile_pcu.csv", index=False)
    print(f"OK: {len(c):,} rows, {c.junction_id.nunique()} junctions, {c.groupby(['junction_id','survey_date']).ngroups} junction-days")


if __name__ == "__main__":
    main()
