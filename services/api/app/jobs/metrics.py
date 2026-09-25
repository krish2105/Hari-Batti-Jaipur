"""Hourly Junction Health metrics for every junction and survey hour -> metrics_hourly table.

Inputs: survey counts per approach and hour (data/processed/tmc_clean.csv via services/ml), the
signal plan (FIELD rows in data/signal_timings.csv, else "Assumed timing – demand-proportional
(2-phase, free left)"), lanes (registry, else ASSUMED). Pedestrians crossing an arm are assumed to
walk during the other phase's green; crossing width = 3.5 m x lanes x 2 directions (ASSUMED).
Run: uv run python -m app.jobs.metrics
"""

import logging

from ml import capacity, metrics
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..db import connect
from ..tables import metrics_hourly

log = logging.getLogger("haribatti.metrics")
DATES = ("2026-05-11", "2026-05-12")


def run() -> int:
    rows = 0
    for date in DATES:
        try:
            ahs = capacity.approach_hours(date)
        except FileNotFoundError as e:
            log.warning("metrics skipped for %s: %s", date, e)
            continue
        by_jh: dict[tuple[str, int], list] = {}
        for a in ahs:
            by_jh.setdefault((a.junction_id, a.hour), []).append(a)
        timing_cache: dict[str, dict] = {}
        batch = []
        for (jid, hour), group in sorted(by_jh.items()):
            timing = timing_cache.setdefault(jid, capacity.junction_timing(jid, "2026-05-11"))
            m = metrics.junction_metrics(metrics.assume_pedestrians(group, timing["green_s"]))
            detail = {
                "approaches": [{**ap, "vc": round(ap["x"], 3)} for ap in m["approaches"]],
                "cycle_s": timing["cycle_s"],
                "green_s": timing["green_s"],
                "Y": timing["Y"],
                "oversaturated": timing["oversaturated"],
                "ped": "ASSUMED widths and walk time",
            }
            batch.append(
                {
                    "junction_id": jid,
                    "survey_date": date,
                    "hour": hour,
                    "red_wait_s": m["red_wait_s"],
                    "cycles_to_clear": m["cycles_to_clear"],
                    "starvation": m["starvation"],
                    "ped_ratio": m["ped_ratio"],
                    "spill_min": m["spill_min"],
                    "health": m["health"],
                    "flow_pcu_h": sum(a.flow_pcu_h for a in group),
                    "detail": detail,
                    "source": f"SURVEY counts + {timing['source']} timing",
                    "timing_label": timing["label"],
                }
            )
        with connect() as c:
            for row in batch:
                stmt = pg_insert(metrics_hourly).values(row)
                c.execute(
                    stmt.on_conflict_do_update(
                        constraint="metrics_key",
                        set_={
                            k: stmt.excluded[k]
                            for k in row
                            if k not in ("junction_id", "survey_date", "hour")
                        },
                    )
                )
        rows += len(batch)
    log.info("metrics_hourly: %d junction-hours", rows)
    return rows


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print({"junction_hours": run()})
