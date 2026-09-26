"""Field study kit (P8 W14): invites, anonymous participants, randomised runs, trimmed traces.

Revision ID: 0010
"""

from alembic import op

from app.tables import study_invites, study_participants, study_runs, study_traces

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None
ORDER = [study_invites, study_participants, study_runs, study_traces]


def upgrade() -> None:
    for t in ORDER:
        t.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    for t in reversed(ORDER):
        t.drop(op.get_bind(), checkfirst=True)
