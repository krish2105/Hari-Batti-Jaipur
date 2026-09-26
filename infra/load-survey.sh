#!/bin/sh
# Load the CONFIDENTIAL survey table onto YOUR production server (P8 W18). Run it yourself, from your laptop:
#   sh infra/load-survey.sh root@<server-ip>
# It copies data/processed/tmc_clean.csv over SSH into the API container (never into git or an image),
# then re-seeds the counts and recomputes the hourly metrics that the fairness audit and junction pages use.
# The rows stay in the server's Postgres (and its encrypted backups); the file itself is deleted afterwards.
set -eu
HOST="${1:?user@server}"
F=data/processed/tmc_clean.csv
[ -f "$F" ] || { echo "missing $F (run scripts/process_tmc.py first)"; exit 1; }
scp -q "$F" "$HOST:/tmp/tmc_clean.csv"
ssh "$HOST" 'set -e; cd /opt/haribatti; C="docker compose -f infra/docker-compose.prod.yml --env-file infra/.env.production";
  $C cp /tmp/tmc_clean.csv api:/app/data/processed/tmc_clean.csv && rm -f /tmp/tmc_clean.csv;
  $C exec -T api uv run --no-sync python -m app.bootstrap;
  $C exec -T -u root api rm -f /app/data/processed/tmc_clean.csv'
echo "survey loaded into the server database, metrics computed, and the file removed again from $HOST"
