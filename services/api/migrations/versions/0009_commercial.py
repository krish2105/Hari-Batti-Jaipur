"""Commercial surfaces (P8 W17): website pilot requests and per-tenant usage metering.

Revision ID: 0009
"""

from alembic import op

from app.tables import leads, usage_daily

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    leads.create(op.get_bind(), checkfirst=True)
    usage_daily.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    usage_daily.drop(op.get_bind(), checkfirst=True)
    leads.drop(op.get_bind(), checkfirst=True)
