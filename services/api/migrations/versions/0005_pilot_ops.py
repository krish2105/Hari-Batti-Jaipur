"""Pilot operations, officer feedback and tenants (P8 W13).

Revision ID: 0005
"""

from alembic import op

from app.tables import (
    insight_feedback,
    officer_notes,
    pilot_kpis,
    pilots,
    tenant_members,
    tenant_sites,
    tenants,
    timing_changes,
    weekly_reviews,
)

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

ORDER = [
    tenants,
    tenant_sites,
    tenant_members,
    pilots,
    pilot_kpis,
    officer_notes,
    insight_feedback,
    weekly_reviews,
    timing_changes,
]


def upgrade() -> None:
    for t in ORDER:
        t.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    for t in reversed(ORDER):
        t.drop(op.get_bind(), checkfirst=True)
