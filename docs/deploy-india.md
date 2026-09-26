# Hosting HariBatti in India

*The website stays on Vercel (static, no personal data). The API, dashboard, database and live feed run on
one server in an Indian region. Nothing is bought or created until the owner picks a provider and budget.*

## Options for the pilot (8 junctions, a few officers, up to a few thousand app users)

Estimates from public price pages in September 2026; confirm on the provider's calculator before buying.

| Option | Server (≈2–4 vCPU, 4–8 GB) | Database | Approx. monthly | MeitY empanelled | Notes |
| --- | --- | --- | --- | --- | --- |
| **E2E Networks** (Delhi/Mumbai) | C3 4 vCPU / 8 GB ≈ ₹2,545 | Postgres in Docker on the same VM (DBaaS from ≈ ₹7,187) | **≈ ₹3,000–4,000** | Yes | INR billing with GST invoice; simplest for a government pilot |
| **AWS Mumbai (ap-south-1)** | t3.medium ≈ US$31–33 | RDS db.t4g.micro ≈ US$5 (or in Docker) | **≈ ₹3,500–5,000** | Yes (Mumbai, Hyderabad) | Most documentation; bills in USD unless via a partner |
| **Azure Central India (Pune)** | B2s ≈ US$30–33 | Postgres in Docker | **≈ ₹3,000–4,000** | Yes | Good if the customer already uses Microsoft |

Plus: domain (≈ ₹1,000/year), object storage for off-server backups (E2E ≈ ₹730/month for 250 GB, or S3 Mumbai).
Recommendation for a police pilot: **E2E Networks** (Indian provider, MeitY empanelled, INR invoices). Move
the database to a managed service when the contract allows.

## One-time setup (≈ 1 hour)

1. Create an Ubuntu 24.04 VM in the chosen Indian region; point two DNS names at it (`api.<domain>`, `dashboard.<domain>`).
2. Firewall: allow 22 (your IP only), 80 and 443; nothing else. `ufw default deny incoming && ufw allow from <your-ip> to any port 22 && ufw allow 80,443/tcp && ufw enable`.
3. Police/vendor feeds (data connectors): prefer a site-to-site VPN or the vendor's IP allow-list; the server only
   makes outgoing, read-only connections (docs/data-connectors.md). Disk encryption: enable the provider's
   encrypted volumes.
4. Install Docker, clone the repository to `/opt/haribatti`, copy `infra/.env.production.example` to
   `infra/.env.production` and fill it in (random `JWT_SECRET`, `POSTGRES_PASSWORD`, `BACKUP_PASSPHRASE`; real admin emails).
5. `docker compose -f infra/docker-compose.prod.yml --env-file infra/.env.production up -d --build` — Caddy fetches
   the TLS certificates automatically. The API refuses to start if any development setting is left on.
6. Set the website's `NEXT_PUBLIC_API_URL=https://api.<domain>` in Vercel so the pilot-request form reaches the API.
7. Turn on automatic deploys: GitHub → Settings → Secrets (`DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`) and
   variables (`API_HOST`, `DEPLOY_ENABLED=true`); then `git tag v1.0.0 && git push --tags`.

## Backups and the restore drill

- The `backup` service writes an AES-256 encrypted `pg_dump` every 24 h and keeps 30 days (`infra/backup.sh`);
  copy `/backups` to object storage in the same region.
- Restore: `BACKUP_PASSPHRASE=… PGHOST=… PGUSER=… PGDATABASE=… sh infra/restore.sh <file.dump.enc>` (it also
  recreates the copilot's read-only role, which a dump does not contain).
- **Drill done on 26 Sep 2026 (local):** encrypted backup of the development database (347 KB) restored into a fresh
  PostGIS container in 11 s; row counts matched for junctions (8), survey counts (16,128), hourly metrics (336),
  phase events (426), tenants (8) and pilot KPIs (33). Repeat the drill monthly on the server and note it here.

## Rollback

- App: deploy the previous tag (`workflow_dispatch` with that tag, or `TAG=v1.0.0 docker compose … up -d`).
- Database: every migration has a downgrade — `docker compose … exec api uv run --no-sync alembic downgrade -1`;
  if in doubt, restore last night's backup.

## After go-live

The uptime ledger (dashboard → System status) starts counting at once; the 30-day, 99% goal is judged from it.
