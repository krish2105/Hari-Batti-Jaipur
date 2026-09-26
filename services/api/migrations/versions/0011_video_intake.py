"""Junction video intake (P8 W15).

Revision ID: 0011
"""

from alembic import op

from app.tables import video_jobs

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    video_jobs.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    video_jobs.drop(op.get_bind(), checkfirst=True)
