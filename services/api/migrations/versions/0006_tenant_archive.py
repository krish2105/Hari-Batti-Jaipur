"""Tenants can be archived (offboarded): hidden, records kept; Hindi text for KPI methods (P8 W13).

Revision ID: 0006
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS archived boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE pilot_kpis ADD COLUMN IF NOT EXISTS method_hi text")
    op.execute("ALTER TABLE pilot_kpis ADD COLUMN IF NOT EXISTS target_hi text")


def downgrade() -> None:
    op.execute("ALTER TABLE pilot_kpis DROP COLUMN IF EXISTS target_hi")
    op.execute("ALTER TABLE pilot_kpis DROP COLUMN IF EXISTS method_hi")
    op.execute("ALTER TABLE tenants DROP COLUMN IF EXISTS archived")
