"""Audit log of sign-ins and exports (W6).

Revision ID: 0002
"""

from alembic import op

from app.tables import audit_log

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    audit_log.create(op.get_bind(), checkfirst=True)
    op.execute("CREATE INDEX IF NOT EXISTS audit_log_ts_idx ON audit_log (ts DESC)")


def downgrade() -> None:
    audit_log.drop(op.get_bind(), checkfirst=True)
