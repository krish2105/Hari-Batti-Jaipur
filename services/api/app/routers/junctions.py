"""Junctions, their survey aggregates and hourly health metrics."""

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select

from .. import data_files as d
from ..db import connect, db_available
from ..tables import metrics_hourly

router = APIRouter(tags=["junctions"])


def junction_payload(r: dict, request: Request | None = None) -> dict:
    jid = r["junction_id"]
    pos = d.positions()[jid]
    lanes, lanes_src = d.lanes_for(jid)
    main = d.main_approaches(jid)
    sides = d.sides().get(jid, {})
    return {
        "id": jid,
        "name": r["junction_name"],
        "tmcCode": r["tmc_code"] or None,
        "controlType": "UNKNOWN",  # signal_type in the registry is VERIFY for all 8
        "lat": pos["lat"],
        "lng": pos["lng"],
        "positionStatus": pos["status"],
        "positionNote": pos["note"],
        "approaches": [
            {
                "id": f"{jid}-{d.slug(n)}",
                "name": n,
                "isMain": n in main,
                "side": sides.get(n),
                "lanes": lanes[n],
                "lanesSource": lanes_src,
            }
            for n in [a.strip() for a in r["approaches_used"].split("|")]
        ],
        "survey": d.survey_summary().get(jid, []),
        "timing": "FIELD" if jid in d.field_timing_junctions() else "ASSUMED",
    }


@router.get("/junctions")
def list_junctions() -> list[dict]:
    """All 8 pilot junctions (data/junction_registry.csv) with position status and survey totals."""
    return [junction_payload(r) for r in d.registry()]


@router.get("/junctions/{junction_id}")
def get_junction(junction_id: str) -> dict:
    r = next((x for x in d.registry() if x["junction_id"] == junction_id.upper()), None)
    if r is None:
        raise HTTPException(404, "Unknown junction — pilot junctions are J01–J08")
    out = junction_payload(r)
    out["hourlyPcu"] = d.hourly_profile().get(r["junction_id"], {})
    return out


def _metrics_rows(junction_id: str | None, date: str | None, frm: int, to: int) -> list[dict]:
    q = select(metrics_hourly).where(metrics_hourly.c.hour >= frm, metrics_hourly.c.hour <= to)
    if junction_id:
        q = q.where(metrics_hourly.c.junction_id == junction_id)
    if date:
        q = q.where(metrics_hourly.c.survey_date == date)
    with connect() as c:
        return [
            dict(r._mapping)
            for r in c.execute(q.order_by(metrics_hourly.c.survey_date, metrics_hourly.c.hour))
        ]


def summarise(rows: list[dict]) -> dict:
    """Flow-weighted averages over the selected hours."""
    if not rows:
        return {}
    w = sum(r["flow_pcu_h"] or 0 for r in rows) or 1

    def avg(k: str) -> float | None:
        vals = [(r[k], r["flow_pcu_h"] or 0) for r in rows if r[k] is not None]
        return round(sum(v * f for v, f in vals) / (sum(f for _, f in vals) or 1), 2) if vals else None

    return {
        "health": avg("health"),
        "redWaitS": avg("red_wait_s"),
        "cyclesToClear": avg("cycles_to_clear"),
        "starvation": avg("starvation"),
        "pedRatio": avg("ped_ratio"),
        "spillMin": round(sum(r["spill_min"] or 0 for r in rows), 1),
        "flowPcu": round(w),
        "worstHour": min(rows, key=lambda r: r["health"] if r["health"] is not None else 101)["hour"],
    }


@router.get("/junctions/{junction_id}/metrics")
def junction_metrics(
    junction_id: str,
    date: str | None = Query(None, description="2026-05-11 or 2026-05-12"),
    frm: int = Query(0, alias="from", ge=0, le=23, description="first clock hour (0 = 00:00)"),
    to: int = Query(23, ge=0, le=23),
) -> dict:
    """Health Score + the five metrics per hour (SURVEY counts + ASSUMED timing)."""
    if not db_available():
        raise HTTPException(503, "Database not running — start it with `make infra`")
    rows = _metrics_rows(junction_id.upper(), date, frm, to)
    if not rows:
        raise HTTPException(
            404, "No metrics yet — run `uv run python -m app.jobs.metrics` (needs tmc_clean.csv)"
        )
    return {
        "junctionId": junction_id.upper(),
        "summary": summarise(rows),
        "hours": [{**r, "hour_start": f"{r['hour']:02d}:00"} for r in rows],  # hour = clock hour
        "source": rows[0]["source"],
        "timingLabel": rows[0]["timing_label"],
    }
