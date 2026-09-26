"""Security readiness (P8 W16): data-subject requests, signed-out sessions and a least-privilege role
for the AI copilot.

copilot_reader can only SELECT the four objects the copilot's SQL guard allows. The API switches to
it (SET LOCAL ROLE) inside every copilot query, so even SQL that slipped past the guard cannot read
users, sign-in codes or the audit log. Creating a role needs CREATEROLE; if the database user lacks
it the migration still succeeds and the API falls back to the guard + read-only transaction.

Revision ID: 0007
"""

from alembic import op

from app.tables import privacy_requests, revoked_tokens

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

COPILOT_OBJECTS = ("copilot_metrics", "copilot_counts_hourly", "junctions", "approaches")


def upgrade() -> None:
    privacy_requests.create(op.get_bind(), checkfirst=True)
    revoked_tokens.create(op.get_bind(), checkfirst=True)
    op.execute(
        f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'copilot_reader') THEN
            CREATE ROLE copilot_reader NOLOGIN;
          END IF;
          EXECUTE 'GRANT copilot_reader TO ' || quote_ident(current_user);
          {" ".join(f"EXECUTE 'GRANT SELECT ON {o} TO copilot_reader';" for o in COPILOT_OBJECTS)}
        EXCEPTION WHEN insufficient_privilege THEN
          RAISE NOTICE 'copilot_reader not created (no CREATEROLE): copilot keeps the SQL guard + read-only transaction';
        END $$;
        """
    )


def downgrade() -> None:
    revoked_tokens.drop(op.get_bind(), checkfirst=True)
    privacy_requests.drop(op.get_bind(), checkfirst=True)
