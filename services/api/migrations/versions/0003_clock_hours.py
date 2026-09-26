"""Copilot views use clock hours.

metrics_hourly.hour is the clock hour (services/ml approach_hours), so hour_start is hour itself.
counts.slot counts 15-min slots from 08:00, so its clock hour is (slot / 4 + 8) % 24.

Revision ID: 0003
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP VIEW IF EXISTS copilot_metrics")
    op.execute("DROP VIEW IF EXISTS copilot_counts_hourly")
    op.execute(
        """
        CREATE VIEW copilot_metrics AS
        SELECT m.junction_id, j.name AS junction_name, m.survey_date, m.hour,
               lpad(m.hour::text, 2, '0') || ':' || '00' AS hour_start,
               m.red_wait_s, m.cycles_to_clear, m.starvation, m.ped_ratio, m.spill_min, m.health,
               m.flow_pcu_h, m.source, m.timing_label
        FROM metrics_hourly m JOIN junctions j ON j.id = m.junction_id
        """
    )
    op.execute(
        """
        CREATE VIEW copilot_counts_hourly AS
        SELECT junction_id, survey_date, (slot / 4 + 8) % 24 AS hour,
               lpad(((slot / 4 + 8) % 24)::text, 2, '0') || ':' || '00' AS hour_start,
               from_approach, to_approach, turn,
               sum(total_veh) AS vehicles, sum(total_pcu) AS pcu, sum(two_wheeler) AS two_wheelers
        FROM counts GROUP BY junction_id, survey_date, slot / 4, from_approach, to_approach, turn
        """
    )


def downgrade() -> None:
    pass  # 0001 recreates the old views on a fresh database
