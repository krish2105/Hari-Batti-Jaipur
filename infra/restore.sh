#!/bin/sh
# Restore an encrypted backup into the database named by PG* variables (P8 W18).
#   BACKUP_PASSPHRASE=... PGHOST=... PGUSER=... PGDATABASE=... sh infra/restore.sh <file.dump.enc>
set -eu
: "${BACKUP_PASSPHRASE:?set BACKUP_PASSPHRASE}"
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass env:BACKUP_PASSPHRASE -in "$1" | pg_restore --no-owner --clean --if-exists -d "${PGDATABASE}"
# roles are cluster-wide and not in a dump: recreate the copilot's read-only role and its grants (migration 0007)
psql -v ON_ERROR_STOP=0 -d "${PGDATABASE}" -c "DO \$\$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'copilot_reader') THEN CREATE ROLE copilot_reader NOLOGIN; END IF;
  EXECUTE 'GRANT copilot_reader TO ' || quote_ident(current_user);
  GRANT SELECT ON copilot_metrics, copilot_counts_hourly, junctions, approaches TO copilot_reader;
END \$\$;"
echo "restore ok: $1 -> ${PGDATABASE}"
