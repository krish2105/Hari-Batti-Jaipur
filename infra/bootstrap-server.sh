#!/bin/sh
# One-command setup of a fresh Ubuntu 24.04 server (E2E Networks or any provider) — P8 W18.
#   ssh root@<server-ip> 'sh -s' < infra/bootstrap-server.sh <server-ip-or-domain> <admin-email> [your-ip-for-ssh]
# With an IP, the hosts are api.<ip-with-dashes>.sslip.io and dashboard.<...>.sslip.io (free DNS names that
# point at the IP, so HTTPS works without buying a domain). With a domain, api.<domain> and dashboard.<domain>
# must already point at the server. Safe to run again: it updates the code and keeps existing secrets.
set -eu
BASE="${1:?server IP or domain}"; ADMIN="${2:?admin email}"; SSH_FROM="${3:-}"
case "$BASE" in
  *[!0-9.]*) API_HOST="api.$BASE"; DASH_HOST="dashboard.$BASE" ;;
  *) D=$(echo "$BASE" | tr . -); API_HOST="api.$D.sslip.io"; DASH_HOST="dashboard.$D.sslip.io" ;;
esac
export DEBIAN_FRONTEND=noninteractive
echo "== packages"; apt-get -qq update && apt-get -qq install -y docker.io docker-compose-v2 git ufw openssl curl >/dev/null
systemctl enable --now docker >/dev/null
if ! swapon --show | grep -q .; then fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile && echo '/swapfile none swap sw 0 0' >> /etc/fstab; fi
echo "== firewall: SSH${SSH_FROM:+ from $SSH_FROM only}, 80, 443"
ufw --force reset >/dev/null
ufw default deny incoming >/dev/null; ufw default allow outgoing >/dev/null
if [ -n "$SSH_FROM" ]; then ufw allow from "$SSH_FROM" to any port 22 proto tcp >/dev/null; else ufw allow 22/tcp >/dev/null; fi
ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null; ufw --force enable >/dev/null
echo "== code"
if [ -d /opt/haribatti/.git ]; then git -C /opt/haribatti pull -q --ff-only; else git clone -q https://github.com/krish2105/Hari-Batti-Jaipur.git /opt/haribatti; fi
cd /opt/haribatti
ENV=infra/.env.production
if [ ! -f "$ENV" ]; then
  echo "== secrets (new, kept only on this server: $ENV)"
  umask 077
  cat > "$ENV" <<EOT
API_HOST=$API_HOST
DASHBOARD_HOST=$DASH_HOST
POSTGRES_PASSWORD=$(openssl rand -hex 24)
JWT_SECRET=$(openssl rand -base64 48 | tr -d '\n=+/')
BACKUP_PASSPHRASE=$(openssl rand -base64 36 | tr -d '\n=+/')
ADMIN_EMAILS=$ADMIN
CORS_ORIGINS=https://$DASH_HOST,https://hari-batti-jaipur.vercel.app
AUTH_DEV_ECHO_OTP=false
AUTH_OPEN_SIGNUP=false
WEB_CONCURRENCY=2
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
ALERT_EMAIL_TO=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
EOT
fi
echo "== build and start (first build takes a few minutes)"
docker compose -f infra/docker-compose.prod.yml --env-file "$ENV" up -d --build
. "./$ENV"
echo "== waiting for https://$API_HOST/ready"
for i in $(seq 1 90); do curl -fsS "https://$API_HOST/ready" >/dev/null 2>&1 && break; sleep 5; done
curl -fsS "https://$API_HOST/ready" && echo
curl -fsS -o /dev/null -w "dashboard %{http_code}\n" "https://$DASH_HOST/en/login"
echo "Done. Dashboard: https://$DASH_HOST  API: https://$API_HOST"
echo "Sign-in code without email: cd /opt/haribatti && docker compose -f infra/docker-compose.prod.yml --env-file $ENV exec api uv run --no-sync python -m app.jobs.login_code $ADMIN"
