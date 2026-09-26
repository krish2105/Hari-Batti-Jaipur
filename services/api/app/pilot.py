"""Pilot operations and tenants (P8 W13): KPI templates, measured baselines, access rules, seeding.

Rules kept here so the router stays thin:
- A KPI value is either measured (with a source label) or null ("not measured yet"). Nothing is
  estimated to fill a gap. The Jaipur baselines that CAN be computed from the May 2026 survey are
  computed live from metrics_hourly and labelled "SURVEY counts + ASSUMED timing".
- The police tenant's sites are only J01-J08 from data/junction_registry.csv (never invented).
- Demo tenants are marked demo=True and hold SIM data only.
"""

import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from . import data_files as d
from .db import connect
from .tables import metrics_hourly, pilot_kpis, pilots, tenant_members, tenant_sites, tenants

SOURCES = ("SIM", "FIELD", "SURVEY", "CROWD", "ITMS")
KINDS = ("police", "campus", "township", "fleet", "other")
JAIPUR = "jaipur-police"
DEMO = "campus-demo-sim"
PEAKS = {"AM": (8, 9, 10), "PM": (17, 18, 19)}
SURVEY_DAY = "2026-05-11"
IST = ZoneInfo("Asia/Kolkata")


def today() -> date:
    """Today in Jaipur (pilot days are counted in IST)."""
    return datetime.now(IST).date()


# Success measures per customer type. Police = the pilot proposal's table (docs-private/00-strategy.md).
# Targets are design goals, not results.
KPI_TEMPLATES: dict[str, list[dict]] = {
    "police": [
        {"key": "vc_over_09", "label": "Approach-peaks above v/c 0.9", "label_hi": "v/c 0.9 से ऊपर वाले दिशा-पीक", "unit": "approach-peaks", "better": "lower",
         "method": "Survey peak PCU ÷ capacity from timings + lanes", "method_hi": "सर्वे का पीक PCU ÷ टाइमिंग और लेन से क्षमता", "target_note": "Flag every approach above 0.9", "target_hi": "0.9 से ऊपर हर दिशा चिह्नित करें"},
        {"key": "red_wait_s", "label": "Average red wait per approach", "label_hi": "हर दिशा पर औसत लाल इंतज़ार", "unit": "s", "better": "lower",
         "method": "Stopwatch timings + survey arrivals", "method_hi": "स्टॉपवॉच टाइमिंग + सर्वे आगमन", "target_note": "−15% via recommended splits", "target_hi": "सुझाए ग्रीन बँटवारे से −15%"},
        {"key": "stops_per_trip", "label": "Stops per corridor trip (J03→J08)", "label_hi": "कॉरिडोर यात्रा में रुकना (J03→J08)", "unit": "stops", "better": "lower",
         "method": "GPS test drives, 20 runs", "method_hi": "GPS टेस्ट ड्राइव, 20 बार", "target_note": "−20% with green-wave speed advice", "target_hi": "ग्रीन-वेव गति सलाह से −20%"},
        {"key": "ped_clearance_pct", "label": "Crossings with enough walk time", "label_hi": "पर्याप्त पैदल समय वाले क्रॉसिंग", "unit": "%", "better": "higher",
         "method": "Tape + timer at 1.0–1.2 m/s walking speed", "method_hi": "फ़ीता + टाइमर, 1.0–1.2 मी/से पैदल गति", "target_note": "100% of crossings", "target_hi": "100% क्रॉसिंग"},
        {"key": "timer_error_s", "label": "App timer error vs the real signal", "label_hi": "ऐप टाइमर बनाम असली सिग्नल की त्रुटि", "unit": "s", "better": "lower",
         "method": "App vs physical signal, stopwatch", "method_hi": "ऐप बनाम असली सिग्नल, स्टॉपवॉच", "target_note": "Under 2 s with a live feed", "target_hi": "लाइव फ़ीड के साथ 2 सेकंड से कम"},
    ],
    "campus": [
        {"key": "gate_wait_s", "label": "Average wait at a gate", "label_hi": "गेट पर औसत इंतज़ार", "unit": "s", "better": "lower",
         "method": "Camera or stopwatch at each gate", "method_hi": "हर गेट पर कैमरा या स्टॉपवॉच", "target_note": "Set after the first two weeks", "target_hi": "पहले दो हफ़्तों के बाद तय होगा"},
        {"key": "peak_queue_veh", "label": "Peak queue at the busiest gate", "label_hi": "सबसे व्यस्त गेट पर अधिकतम कतार", "unit": "vehicles", "better": "lower",
         "method": "Camera count at the peak 15 minutes", "method_hi": "पीक के 15 मिनट में कैमरा गिनती", "target_note": "Set after the first two weeks", "target_hi": "पहले दो हफ़्तों के बाद तय होगा"},
        {"key": "gate_throughput_vph", "label": "Gate throughput at peak", "label_hi": "पीक पर गेट से निकले वाहन", "unit": "veh/h", "better": "higher",
         "method": "Camera count", "method_hi": "कैमरा गिनती", "target_note": "Set after the first two weeks", "target_hi": "पहले दो हफ़्तों के बाद तय होगा"},
        {"key": "reports_resolved_pct", "label": "Resident reports resolved in 7 days", "label_hi": "7 दिन में हल हुई शिकायतें", "unit": "%", "better": "higher",
         "method": "Citizen reports in the app", "method_hi": "ऐप में नागरिक शिकायतें", "target_note": "80%", "target_hi": "80%"},
    ],
    "fleet": [
        {"key": "eta_error_min", "label": "ETA error", "label_hi": "पहुँचने के समय की त्रुटि", "unit": "min", "better": "lower",
         "method": "Predicted vs actual arrival, all trips", "method_hi": "अनुमानित बनाम असली पहुँच, सभी यात्राएँ", "target_note": "Set after the first two weeks", "target_hi": "पहले दो हफ़्तों के बाद तय होगा"},
        {"key": "stops_per_trip", "label": "Signal stops per trip", "label_hi": "प्रति यात्रा सिग्नल पर रुकना", "unit": "stops", "better": "lower",
         "method": "Vehicle GPS", "method_hi": "वाहन GPS", "target_note": "Set after the first two weeks", "target_hi": "पहले दो हफ़्तों के बाद तय होगा"},
        {"key": "idle_min", "label": "Idle time per trip", "label_hi": "प्रति यात्रा खड़े रहने का समय", "unit": "min", "better": "lower",
         "method": "Vehicle GPS (speed < 5 km/h)", "method_hi": "वाहन GPS (गति < 5 किमी/घं)", "target_note": "Set after the first two weeks", "target_hi": "पहले दो हफ़्तों के बाद तय होगा"},
    ],
}  # fmt: skip
KPI_TEMPLATES["township"] = KPI_TEMPLATES["campus"]
KPI_TEMPLATES["other"] = KPI_TEMPLATES["campus"]

REPORT_SECTIONS = ("kpis", "reviews", "feedback", "changes", "notes", "sources")
DEFAULT_TEMPLATE = {
    "title": "Pilot Evidence Pack",
    "sections": list(REPORT_SECTIONS),
    "footer": "Read-only analysis. No signal was controlled by HariBatti.",
}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def jaipur_sites() -> list[dict]:
    """J01-J08 exactly as the registry names them."""
    return [
        {
            "site_id": r["junction_id"],
            "name": r["junction_name"],
            "kind": "junction",
            "lat": None,
            "lng": None,
            "source": "SURVEY",
        }
        for r in d.registry()
    ]


def registry_ids() -> set[str]:
    return {r["junction_id"] for r in d.registry()}


# ---- access --------------------------------------------------------------------------------------


def visible_tenants(user: dict) -> list[dict]:
    """Admins see every active tenant; others see tenants open to all plus those they are members of.
    Archived (offboarded) tenants are hidden from everyone; their records are kept."""
    with connect() as c:
        rows = [
            dict(r._mapping)
            for r in c.execute(
                select(tenants)
                .where(tenants.c.archived.is_(False))
                .order_by(tenants.c.demo, tenants.c.created_at)
            )
        ]
        mine = {
            r.tenant_id: r.role
            for r in c.execute(select(tenant_members).where(tenant_members.c.email == user["email"]))
        }
    if user["role"] == "Admin":
        return rows
    return [r for r in rows if r["open_to_all"] or r["id"] in mine]


def can_see(user: dict, tenant_id: str) -> bool:
    return any(t["id"] == tenant_id for t in visible_tenants(user))


# ---- measured baselines (Jaipur) -----------------------------------------------------------------


def survey_baselines(day: str = SURVEY_DAY) -> dict[str, dict]:
    """KPI baselines that the May 2026 survey + assumed timings can honestly give. Empty without metrics."""
    with connect() as c:
        rows = c.execute(select(metrics_hourly).where(metrics_hourly.c.survey_date == day)).all()
    if not rows:
        return {}
    peak_vc: dict[tuple[str, str, str], float] = {}
    for r in rows:
        for name, hours in PEAKS.items():
            if r.hour in hours:
                for ap in (r.detail or {}).get("approaches", []):
                    k = (r.junction_id, ap["approach"], name)
                    peak_vc[k] = max(peak_vc.get(k, 0.0), float(ap.get("vc") or 0))
    over = sum(v > 0.9 for v in peak_vc.values())
    flow = sum(r.flow_pcu_h or 0 for r in rows if r.red_wait_s is not None) or 1
    red = sum((r.red_wait_s or 0) * (r.flow_pcu_h or 0) for r in rows if r.red_wait_s is not None) / flow
    src = "SURVEY counts + ASSUMED timing"
    return {
        "vc_over_09": {
            "value": over,
            "source": src,
            "note": f"{over} of {len(peak_vc)} approach-peaks (AM 08–11, PM 17–20, {day})",
            "noteHi": f"{len(peak_vc)} में से {over} दिशा-पीक (सुबह 08–11, शाम 17–20, {day})",
        },
        "red_wait_s": {
            "value": round(red, 1),
            "source": src,
            "note": f"Flow-weighted mean over all hours, {day}; timings assumed until stopwatch data",
            "noteHi": f"सभी घंटों का ट्रैफ़िक-भारित औसत, {day}; स्टॉपवॉच डेटा तक टाइमिंग मान ली गई",
        },
    }


def kpi_rows(pilot_id: int, tenant_id: str) -> list[dict]:
    """KPIs of one pilot; for Jaipur, empty baselines are filled live from the survey (labelled)."""
    with connect() as c:
        rows = [
            dict(r._mapping)
            for r in c.execute(
                select(pilot_kpis).where(pilot_kpis.c.pilot_id == pilot_id).order_by(pilot_kpis.c.id)
            )
        ]
    auto = survey_baselines() if tenant_id == JAIPUR else {}
    out = []
    for r in rows:
        b = auto.get(r["key"]) if r["baseline_value"] is None else None
        out.append({
            "id": r["id"], "key": r["key"], "label": r["label"], "labelHi": r["label_hi"], "unit": r["unit"], "better": r["better"],
            "method": r["method"], "methodHi": r["method_hi"], "targetNote": r["target_note"], "targetHi": r["target_hi"],
            "baseline": {"value": b["value"], "source": b["source"], "note": b["note"], "noteHi": b.get("noteHi"), "auto": True} if b
            else {"value": r["baseline_value"], "source": r["baseline_source"], "note": r["baseline_note"], "auto": False},
            "current": {"value": r["current_value"], "source": r["current_source"], "note": r["current_note"]},
            "change": change(r["current_value"], (b or {}).get("value", r["baseline_value"])),
            "updatedBy": r["updated_by"], "updatedAt": r["updated_at"].isoformat() if r["updated_at"] else None,
        })  # fmt: skip
    return out


def change(current: float | None, baseline: float | None) -> dict | None:
    """Current vs baseline, only when both were measured."""
    if current is None or baseline is None:
        return None
    return {
        "abs": round(current - baseline, 2),
        "pct": None if baseline == 0 else round(100 * (current - baseline) / baseline, 1),
    }


def pilot_day(start: date | None, end: date | None, on: date | None = None) -> dict:
    """Where the pilot is: not started / day n of N / ended."""
    now = on or today()
    if start is None:
        return {
            "status": "not_started",
            "day": None,
            "days": (end - start).days + 1 if start and end else None,
        }
    days = (end - start).days + 1 if end else None
    if now < start:
        return {"status": "scheduled", "day": 0, "days": days}
    if end and now > end:
        return {"status": "ended", "day": days, "days": days}
    return {"status": "running", "day": (now - start).days + 1, "days": days}


# ---- creation and seeding ------------------------------------------------------------------------


def create_tenant(c, t: dict, sites: list[dict], members: list[dict], created_by: str | None) -> None:
    c.execute(pg_insert(tenants).values(
        id=t["id"], name=t["name"], kind=t["kind"], display_name=t.get("display_name") or t["name"], data_sources=t.get("data_sources", []),
        report_template=t.get("report_template") or DEFAULT_TEMPLATE, open_to_all=t.get("open_to_all", False), demo=t.get("demo", False),
        created_by=created_by,
    ).on_conflict_do_nothing(index_elements=["id"]))  # fmt: skip
    for s in sites:
        c.execute(pg_insert(tenant_sites).values(tenant_id=t["id"], **s).on_conflict_do_nothing())
    for m in members:
        c.execute(
            pg_insert(tenant_members)
            .values(tenant_id=t["id"], email=m["email"].lower(), role=m["role"])
            .on_conflict_do_nothing()
        )


def create_pilot(
    c,
    tenant_id: str,
    kind: str,
    name: str,
    start: date | None,
    end: date | None,
    keys: list[str] | None,
    created_by: str | None,
) -> int:
    pid = c.execute(
        pilots.insert()
        .values(tenant_id=tenant_id, name=name, start_date=start, end_date=end, created_by=created_by)
        .returning(pilots.c.id)
    ).scalar_one()
    for k in KPI_TEMPLATES[kind]:
        if keys is None or k["key"] in keys:
            c.execute(pilot_kpis.insert().values(pilot_id=pid, **k))
    return pid


def seed() -> dict:
    """Jaipur police tenant (open to all officers) and the SIM campus demo. Idempotent."""
    made = []
    with connect() as c:
        have = {r.id for r in c.execute(select(tenants.c.id))}
        if JAIPUR not in have:
            create_tenant(c, {"id": JAIPUR, "name": "Jaipur Traffic Police", "kind": "police", "display_name": "Jaipur Traffic Police — Mansarovar corridor pilot",
                              "data_sources": ["SURVEY", "SIM"], "open_to_all": True,
                              "report_template": {**DEFAULT_TEMPLATE, "title": "Mansarovar Corridor Pilot — Evidence Pack"}}, jaipur_sites(), [], "seed")  # fmt: skip
            create_pilot(c, JAIPUR, "police", "Mansarovar corridor pilot (60 days)", None, None, None, "seed")
            made.append(JAIPUR)
        if DEMO not in have:
            gates = [{"site_id": f"G{i}", "name": n, "kind": "gate", "lat": None, "lng": None, "source": "SIM"}
                     for i, n in enumerate(["Main Gate", "North Gate", "Hostel Gate", "Service Gate"], start=1)]  # fmt: skip
            create_tenant(c, {"id": DEMO, "name": "Campus Demo – SIM", "kind": "campus", "display_name": "Campus Demo – SIM",
                              "data_sources": ["SIM"], "demo": True, "open_to_all": True,
                              "report_template": {**DEFAULT_TEMPLATE, "title": "Campus gate pilot — demo (SIM)"}}, gates, [], "seed")  # fmt: skip
            create_pilot(c, DEMO, "campus", "Campus gate pilot — demo", None, None, None, "seed")
            made.append(DEMO)
        c.execute(
            update(tenants).where(tenants.c.id == DEMO).values(open_to_all=True)
        )  # the SIM demo is for every user
        # KPI rows created before the Hindi columns existed get their Hindi text from the templates
        for tpl in (k for kind in ("police", "campus", "fleet") for k in KPI_TEMPLATES[kind]):
            c.execute(
                update(pilot_kpis)
                .where(pilot_kpis.c.method == tpl["method"], pilot_kpis.c.method_hi.is_(None))
                .values(method_hi=tpl["method_hi"], target_hi=tpl["target_hi"])
            )
    return {"created": made}
