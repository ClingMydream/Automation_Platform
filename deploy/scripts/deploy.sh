#!/usr/bin/env bash
set -euo pipefail

cd /opt/automation-platform

if [ ! -f .env ]; then
  echo ".env is missing. Copy .env.example to .env and change all passwords first."
  exit 1
fi

docker compose pull || true
docker compose up -d --build --remove-orphans
docker compose ps
