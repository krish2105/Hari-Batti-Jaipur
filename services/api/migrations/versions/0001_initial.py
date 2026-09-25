"""Initial schema: junctions, approaches, phase events, counts, hourly metrics, reports, users.

Revision ID: 0001
"""

from alembic import op

from app.tables import metadata

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    metadata.create_all(op.get_bind())
    # PostGIS geography points (kept in sync with lat/lng by the seed job).
    op.execute("ALTER TABLE junctions ADD COLUMN IF NOT EXISTS geom geography(Point, 4326)")
    op.execute("ALTER TABLE citizen_reports ADD COLUMN IF NOT EXISTS geom geography(Point, 4326)")
    op.execute("CREATE INDEX IF NOT EXISTS junctions_geom_idx ON junctions USING gist (geom)")
    op.execute("CREATE INDEX IF NOT EXISTS reports_geom_idx ON citizen_reports USING gist (geom)")
    op.execute("CREATE INDEX IF NOT EXISTS metrics_j_idx ON metrics_hourly (junction_id, survey_date, hour)")
    # Views the AI Copilot may read (it runs inside a READ ONLY transaction as well).
    op.execute(
        """
        CREATE OR REPLACE VIEW copilot_metrics AS
        SELECT m.junction_id, j.name AS junction_name, m.survey_date, m.hour,
               lpad(((m.hour + 8) % 24)::text, 2, '0') || ':' || '00' AS hour_start,
               m.red_wait_s, m.cycles_to_clear, m.starvation, m.ped_ratio, m.spill_min, m.health,
               m.flow_pcu_h, m.source, m.timing_label
        FROM metrics_hourly m JOIN junctions j ON j.id = m.junction_id
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW copilot_counts_hourly AS
        SELECT junction_id, survey_date, slot / 4 AS hour,
               lpad((((slot / 4) + 8) % 24)::text, 2, '0') || ':' || '00' AS hour_start,
               from_approach, to_approach, turn,
               sum(total_veh) AS vehicles, sum(total_pcu) AS pcu, sum(two_wheeler) AS two_wheelers
        FROM counts GROUP BY junction_id, survey_date, slot / 4, from_approach, to_approach, turn
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS copilot_counts_hourly")
    op.execute("DROP VIEW IF EXISTS copilot_metrics")
    metadata.drop_all(op.get_bind())
