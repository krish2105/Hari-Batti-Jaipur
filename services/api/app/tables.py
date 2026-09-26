"""Database tables (PostgreSQL + PostGIS). Created by the Alembic migration in migrations/.

Read-only by design: nothing here stores or sends a command to a signal.
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

# geom columns are PostGIS geography(Point, 4326); declared in the migration with raw SQL and read
# back with ST_Y/ST_X, so SQLAlchemy does not need GeoAlchemy.
junctions = Table(
    "junctions",
    metadata,
    Column("id", String(3), primary_key=True),  # J01-J08 from data/junction_registry.csv
    Column("name", Text, nullable=False),
    Column("tmc_code", Text),
    Column("control_type", Text, nullable=False, server_default="UNKNOWN"),
    Column("coord_status", Text, nullable=False),  # REGISTRY | CANDIDATE | PLACEHOLDER
    Column("lat", Float),
    Column("lng", Float),
)

approaches = Table(
    "approaches",
    metadata,
    Column("id", Text, primary_key=True),  # e.g. J04-durgapur
    Column("junction_id", String(3), ForeignKey("junctions.id"), nullable=False),
    Column("name", Text, nullable=False),
    Column("side", String(1)),  # schematic side W/N/E/S from the survey turn labels
    Column("is_main", Boolean, nullable=False),
    Column("bearing", Float),
    Column("lanes", Integer, nullable=False),
    Column("lanes_source", Text, nullable=False),  # registry | ASSUMED
    Column("crossing_width_m", Float),
    Column("crossing_width_source", Text),
)

phase_events = Table(
    "phase_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("junction_id", String(3), nullable=False, index=True),
    Column("approach_id", Text, nullable=False),
    Column("colour", Text, nullable=False),
    Column("start_ts", DateTime(timezone=True), nullable=False, index=True),
    Column("end_ts", DateTime(timezone=True)),
    Column("source", Text, nullable=False),  # SIM | CROWD | ITMS
    Column("sim_clock", Text),
)

counts = Table(
    "counts",
    metadata,
    Column("junction_id", String(3), nullable=False),
    Column("survey_date", Text, nullable=False),
    Column("movement", Integer, nullable=False),
    Column("from_approach", Text, nullable=False),
    Column("to_approach", Text, nullable=False),
    Column("turn", String(1), nullable=False),
    Column("slot", Integer, nullable=False),
    Column("two_wheeler", Float),
    Column("car_auto", Float),
    Column("heavy", Float),
    Column("slow", Float),
    Column("total_veh", Float, nullable=False),
    Column("total_pcu", Float, nullable=False),
    UniqueConstraint("junction_id", "survey_date", "movement", "slot", name="counts_key"),
)

metrics_hourly = Table(
    "metrics_hourly",
    metadata,
    Column("junction_id", String(3), nullable=False),
    Column("survey_date", Text, nullable=False),
    Column("hour", Integer, nullable=False),  # 0 = 08:00-09:00
    Column("red_wait_s", Float),
    Column("cycles_to_clear", Float),
    Column("starvation", Float),
    Column("ped_ratio", Float),
    Column("spill_min", Float),
    Column("health", Float),
    Column("flow_pcu_h", Float),
    Column("detail", JSONB),  # per-approach metrics
    Column("source", Text, nullable=False),  # e.g. "SURVEY counts + ASSUMED timing"
    Column("timing_label", Text),
    UniqueConstraint("junction_id", "survey_date", "hour", name="metrics_key"),
)

citizen_reports = Table(
    "citizen_reports",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("type", Text, nullable=False),  # broken | hidden | timing_bad | other
    Column("junction_id", String(3)),
    Column("lat", Float),
    Column("lng", Float),
    Column("note", Text),
    Column("photo_url", Text),
    Column("status", Text, nullable=False, server_default="New"),  # New | Assigned | Fixed
    Column("group_key", Text),  # duplicate grouping
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", Text, nullable=False, unique=True),
    Column("role", Text, nullable=False),  # Viewer | Operator | Admin
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

otp_codes = Table(
    "otp_codes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", Text, nullable=False, index=True),
    Column("code_hash", Text, nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("used", Boolean, nullable=False, server_default="false"),
    Column("attempts", Integer, nullable=False, server_default="0"),
)

plan_runs = Table(
    "plan_runs",
    metadata,
    Column("id", Text, primary_key=True),
    Column("status", Text, nullable=False),  # queued | running | done | failed
    Column("request", JSONB, nullable=False),
    Column("result", JSONB),
    Column("error", Text),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)


audit_log = Table(
    "audit_log",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ts", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("email", Text),
    Column("role", Text),
    Column("action", Text, nullable=False),  # login | export_pdf | export_csv | plan_run | copilot_ask
    Column("detail", JSONB),
)


# Per-tenant connector mappings saved from the dashboard (P8 W12). The YAML file holds the defaults.
connector_mappings = Table(
    "connector_mappings",
    metadata,
    Column("connector_id", Text, primary_key=True),
    Column("tenant", Text, nullable=False),
    Column("mapping", JSONB, nullable=False),
    Column("updated_by", Text),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


# ---- Pilot operations, officer feedback and tenants (P8 W13) ----
# A tenant is one customer: the Jaipur Traffic Police pilot, or a campus / township / fleet.
# Every row below carries tenant_id so one tenant never sees another's notes or reviews.
tenants = Table(
    "tenants",
    metadata,
    Column("id", Text, primary_key=True),  # slug, e.g. "jaipur-police"
    Column("name", Text, nullable=False),
    Column("kind", Text, nullable=False),  # police | campus | township | fleet | other
    Column("display_name", Text),  # branding is the name only (no customer logos without permission)
    Column(
        "data_sources", JSONB, nullable=False, server_default="[]"
    ),  # e.g. ["SURVEY", "SIM", "connector:demo-replay"]
    Column("report_template", JSONB, nullable=False, server_default="{}"),  # title, sections, footer
    Column("open_to_all", Boolean, nullable=False, server_default="false"),  # every signed-in user may see it
    Column("demo", Boolean, nullable=False, server_default="false"),  # demo tenants hold SIM data only
    Column("archived", Boolean, nullable=False, server_default="false"),  # offboarded: hidden, records kept
    Column("created_by", Text),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

# Sites are junctions (police tenant: only J01-J08 from the registry) or gates for other customers.
tenant_sites = Table(
    "tenant_sites",
    metadata,
    Column("tenant_id", Text, ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
    Column("site_id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    Column("kind", Text, nullable=False, server_default="junction"),  # junction | gate
    Column("lat", Float),
    Column("lng", Float),
    Column(
        "source", Text, nullable=False
    ),  # where the site comes from: SURVEY (registry) | SIM (demo) | FIELD
)

tenant_members = Table(
    "tenant_members",
    metadata,
    Column("tenant_id", Text, ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
    Column("email", Text, primary_key=True),
    Column("role", Text, nullable=False),  # Viewer | Operator | Admin (within this tenant)
)

pilots = Table(
    "pilots",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("tenant_id", Text, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("name", Text, nullable=False),
    Column("start_date", Date),  # null = not started yet
    Column("end_date", Date),
    Column("created_by", Text),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

# Baseline / current / target per success measure. A null value means "not measured yet" and is
# shown as a placeholder: we never fill a KPI with a number nobody measured.
pilot_kpis = Table(
    "pilot_kpis",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("pilot_id", Integer, ForeignKey("pilots.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("key", Text, nullable=False),
    Column("label", Text, nullable=False),
    Column("label_hi", Text),
    Column("unit", Text, nullable=False),
    Column("better", Text, nullable=False),  # lower | higher
    Column("method", Text, nullable=False),  # how the baseline is measured
    Column("method_hi", Text),
    Column("target_note", Text),  # e.g. "-15% via recommended splits" (a design goal, not a result)
    Column("target_hi", Text),
    Column("baseline_value", Float),
    Column("baseline_source", Text),
    Column("baseline_note", Text),
    Column("current_value", Float),
    Column("current_source", Text),
    Column("current_note", Text),
    Column("updated_by", Text),
    Column("updated_at", DateTime(timezone=True)),
    UniqueConstraint("pilot_id", "key", name="pilot_kpi_key"),
)

officer_notes = Table(
    "officer_notes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("tenant_id", Text, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("site_id", Text, nullable=False),
    Column("approach", Text),  # the pin: which approach the note is about (optional)
    Column("text", Text, nullable=False),
    Column("pinned", Boolean, nullable=False, server_default="false"),
    Column("resolved", Boolean, nullable=False, server_default="false"),
    Column("author", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

insight_feedback = Table(
    "insight_feedback",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("tenant_id", Text, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
    Column(
        "insight", Text, nullable=False
    ),  # stable key, e.g. "audit.top-fixes" or "junction.J05.worst-hour"
    Column("page", Text),
    Column("useful", Boolean, nullable=False),
    Column("comment", Text),
    Column("email", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    UniqueConstraint(
        "tenant_id", "insight", "email", name="feedback_once"
    ),  # one vote per person, can change
)

weekly_reviews = Table(
    "weekly_reviews",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("pilot_id", Integer, ForeignKey("pilots.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("week_start", Date, nullable=False),
    Column("answers", JSONB, nullable=False),
    Column("email", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    UniqueConstraint("pilot_id", "week_start", "email", name="review_once_a_week"),
)

# Timing changes the police made in their own system, entered by them for the record. HariBatti
# never makes these changes; this is a log so before/after can be measured honestly.
timing_changes = Table(
    "timing_changes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("tenant_id", Text, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("site_id", Text, nullable=False),
    Column("changed_on", Date, nullable=False),
    Column("time_window", Text),
    Column("before", Text, nullable=False),
    Column("after", Text, nullable=False),
    Column("reason", Text),
    Column("entered_by", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)


# ---- Data protection (P8 W16) ----
# DPDP Act 2023: a person can export the data we hold about them and ask for it to be erased.
privacy_requests = Table(
    "privacy_requests",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", Text, nullable=False),
    Column("kind", Text, nullable=False),  # erase | correct
    Column("note", Text),
    Column("status", Text, nullable=False, server_default="open"),  # open | done | rejected
    Column("handled_by", Text),
    Column("handled_at", DateTime(timezone=True)),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

# Signed-out sessions (ASVS 3.3.1): a token's id stays here until the token would have expired anyway.
revoked_tokens = Table(
    "revoked_tokens",
    metadata,
    Column("jti", Text, primary_key=True),
    Column("expires_at", DateTime(timezone=True), nullable=False),
)


# ---- Monitoring (P8 W11) ----
alerts = Table(
    "alerts",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("key", Text, nullable=False, index=True),  # e.g. feed_stale:SIM, junction_dark:J05
    Column("kind", Text, nullable=False),  # feed_stale | junction_dark | impossible
    Column("source", Text),
    Column("junction_id", Text),
    Column("message", Text, nullable=False),
    Column("opened_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("closed_at", DateTime(timezone=True)),
)

# One row per service per minute; daily uptime % = ok rows / all rows (the 30-day, 99% goal).
uptime_checks = Table(
    "uptime_checks",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ts", DateTime(timezone=True), server_default=func.now(), nullable=False, index=True),
    Column("service", Text, nullable=False),  # api | database | redis | signal_feed
    Column("ok", Boolean, nullable=False),
)


# ---- Commercial surfaces (P8 W17) ----
# Pilot / contact requests from the website form (no trackers; spam checks before storing).
leads = Table(
    "leads",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", Text, nullable=False),
    Column("organisation", Text, nullable=False),
    Column("role", Text),
    Column("email", Text, nullable=False),
    Column("phone", Text),
    Column(
        "offer", Text, nullable=False
    ),  # pilot | audit | signal_command | citizen_data | fleet_api | other
    Column("city", Text),
    Column("message", Text),
    Column("status", Text, nullable=False, server_default="new"),  # new | contacted | closed
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

# Usage metering: API calls per tenant per day (for invoice support; no payment processing).
usage_daily = Table(
    "usage_daily",
    metadata,
    Column("day", Date, primary_key=True),
    Column("tenant_id", Text, primary_key=True),
    Column("email", Text, primary_key=True),
    Column("calls", Integer, nullable=False, server_default="0"),
)


# ---- Field study kit (P8 W14): 20 GPS test drives, advice ON vs OFF ----
# Invite codes are stored hashed. Participants are random IDs (no name, no email, no phone).
study_invites = Table(
    "study_invites",
    metadata,
    Column("code_hash", Text, primary_key=True),
    Column("label", Text, nullable=False),
    Column("max_participants", Integer, nullable=False, server_default="30"),
    Column("used", Integer, nullable=False, server_default="0"),
    Column("active", Boolean, nullable=False, server_default="true"),
    Column("created_by", Text),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

study_participants = Table(
    "study_participants",
    metadata,
    Column("id", Text, primary_key=True),  # e.g. P-7K3QX9
    Column("vehicle", Text, nullable=False),  # car | scooter | motorbike | auto
    Column("invite_hash", Text, nullable=False),
    Column("consent_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("withdrawn", Boolean, nullable=False, server_default="false"),
)

study_runs = Table(
    "study_runs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "participant_id",
        Text,
        ForeignKey("study_participants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("arm", Text, nullable=False),  # advice | control (assigned by the server, never chosen)
    Column("status", Text, nullable=False, server_default="started"),  # started | uploaded
    Column("direction", Text),  # east | west
    Column("points_kept", Integer),
    Column("points_trimmed", Integer),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("uploaded_at", DateTime(timezone=True)),
)

# Raw 1 Hz trace after trimming the first and last 200 m; deleted after 30 days (jobs/retention.py).
study_traces = Table(
    "study_traces",
    metadata,
    Column("run_id", Integer, ForeignKey("study_runs.id", ondelete="CASCADE"), primary_key=True),
    Column("points", JSONB, nullable=False),  # [[t_s, lat, lng, speed_kmh], ...]
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)
