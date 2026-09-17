#!/usr/bin/env sh
set -eu

APP_DIR=/opt/automation-platform
CERT_PATH="$APP_DIR/letsencrypt/live/xiaomeiqaq.top/fullchain.pem"

# Renew only when fewer than 30 days remain, avoiding unnecessary web-service restarts.
if openssl x509 -checkend 2592000 -noout -in "$CERT_PATH"; then
  exit 0
fi

cd "$APP_DIR"
docker compose stop frontend
trap 'docker compose start frontend' EXIT
docker run --rm -p 80:80 \
  -v "$APP_DIR/letsencrypt:/etc/letsencrypt" \
  certbot/certbot renew --standalone --non-interactive --quiet
