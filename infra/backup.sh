#!/bin/sh
# Encrypted Postgres backup (P8 W18): pg_dump (custom format) -> AES-256 (openssl, PBKDF2) -> BACKUP_DIR.
# Keeps 30 days. Copy BACKUP_DIR to object storage in the same Indian region for off-server copies.
set -eu
: "${BACKUP_PASSPHRASE:?set BACKUP_PASSPHRASE}"
DIR="${BACKUP_DIR:-/backups}"
mkdir -p "$DIR"
F="$DIR/haribatti-$(date -u +%Y%m%dT%H%M%SZ).dump.enc"
pg_dump -Fc --no-owner | openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -pass env:BACKUP_PASSPHRASE -out "$F"
test -s "$F"
find "$DIR" -name 'haribatti-*.dump.enc' -mtime +30 -delete
echo "backup ok: $F ($(wc -c < "$F") bytes)"
