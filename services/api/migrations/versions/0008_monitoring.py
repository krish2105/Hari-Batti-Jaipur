"""Monitoring (P8 W11): alerts and the uptime ledger.

Revision ID: 0008
"""

from alembic import op

from app.tables import alerts, uptime_checks

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    alerts.create(op.get_bind(), checkfirst=True)
    uptime_checks.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    uptime_checks.drop(op.get_bind(), checkfirst=True)
    alerts.drop(op.get_bind(), checkfirst=True)
