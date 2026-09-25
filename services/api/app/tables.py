"""Database tables (PostgreSQL + PostGIS). Created by the Alembic migration in migrations/.

Read-only by design: nothing here stores or sends a command to a signal.
"""

from sqlalchemy import (
    Boolean,
    Column,
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
