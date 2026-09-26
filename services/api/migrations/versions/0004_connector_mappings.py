"""Per-tenant connector mappings (P8 W12).

Revision ID: 0004
"""

from alembic import op

from app.tables import connector_mappings

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connector_mappings.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    connector_mappings.drop(op.get_bind(), checkfirst=True)
