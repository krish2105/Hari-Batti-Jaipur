"""Load junctions, approaches, survey counts and admin users into Postgres (idempotent).

Run: uv run python -m app.jobs.seed   (make api runs it automatically)
Counts come only from data/processed/tmc_clean.csv (local, confidential; skipped if absent).
"""

import csv
import logging

from sqlalchemy import delete, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .. import data_files as d
from ..config import settings
from ..db import connect
from ..tables import approaches, counts, junctions, users

log = logging.getLogger("haribatti.seed")
HEAVY = ("tractor_lcv_minibus", "axle_truck_bus", "truck_trailer_mav")
SLOW = ("cycle", "cycle_rickshaw", "hand_cart", "horse_drawn", "bullock_cart")


def seed_junctions() -> int:
    pos = d.positions()
    sides = d.sides()
    with connect() as c:
        for r in d.registry():
            jid = r["junction_id"]
            p = pos[jid]
            row = {
                "id": jid,
                "name": r["junction_name"],
                "tmc_code": r["tmc_code"] or None,
                "control_type": "UNKNOWN",
                "coord_status": p["status"],
                "lat": p["lat"],
                "lng": p["lng"],
            }
            c.execute(pg_insert(junctions).values(row).on_conflict_do_update(index_elements=["id"], set_=row))
            if p["lat"] is not None:
                c.execute(
                    text(
                        "UPDATE junctions SET geom = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography "
                        "WHERE id = :id"
                    ),
                    {"lng": p["lng"], "lat": p["lat"], "id": jid},
                )
            else:
                c.execute(text("UPDATE junctions SET geom = NULL WHERE id = :id"), {"id": jid})
            lanes, lanes_src = d.lanes_for(jid)
            main = d.main_approaches(jid)
            for name in [a.strip() for a in r["approaches_used"].split("|")]:
                width = lanes[name] * 2 * 3.5  # ASSUMED: both directions, 3.5 m per lane
                arow = {
                    "id": f"{jid}-{d.slug(name)}",
                    "junction_id": jid,
                    "name": name,
                    "side": sides.get(jid, {}).get(name),
                    "is_main": name in main,
                    "lanes": lanes[name],
                    "lanes_source": lanes_src,
                    "crossing_width_m": width,
                    "crossing_width_source": "ASSUMED",
                }
                c.execute(
                    pg_insert(approaches).values(arow).on_conflict_do_update(index_elements=["id"], set_=arow)
                )
    return len(d.registry())


def seed_counts() -> int:
    """Survey counts per movement and 15-min slot (only if the local tmc_clean.csv exists)."""
    if not d.TMC.exists():
        log.warning("data/processed/tmc_clean.csv not found (confidential, not in git) — counts not loaded")
        return 0
    batch = []
    with d.TMC.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):

            def num(k: str, row: dict = r) -> float:
                return float(row[k] or 0)

            batch.append(
                {
                    "junction_id": r["junction_id"],
                    "survey_date": r["survey_date"],
                    "movement": int(r["movement"]),
                    "from_approach": r["from_approach"],
                    "to_approach": r["to_approach"],
                    "turn": r["turn"],
                    "slot": int(r["slot"]),
                    "two_wheeler": num("two_wheeler"),
                    "car_auto": num("car_taxi_auto_pickup"),
                    "heavy": sum(num(k) for k in HEAVY),
                    "slow": sum(num(k) for k in SLOW),
                    "total_veh": num("total_veh"),
                    "total_pcu": num("total_pcu"),
                }
            )
    with connect() as c:
        c.execute(delete(counts))
        for i in range(0, len(batch), 2000):
            c.execute(counts.insert(), batch[i : i + 2000])
    return len(batch)


def seed_users() -> int:
    emails = [e.strip().lower() for e in settings().admin_emails.split(",") if e.strip()]
    with connect() as c:
        for e in emails:
            c.execute(
                pg_insert(users)
                .values(email=e, role="Admin")
                .on_conflict_do_update(index_elements=["email"], set_={"role": "Admin"})
            )
    return len(emails)


def run() -> dict:
    out = {"junctions": seed_junctions(), "counts": seed_counts(), "admins": seed_users()}
    log.info("seeded %s", out)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())
