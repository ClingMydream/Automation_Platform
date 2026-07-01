#!/usr/bin/env bash
set -euo pipefail

echo "[1/6] Install packages"
dnf install -y git docker-ce docker-compose-plugin firewalld
if dnf install -y fail2ban; then
  HAS_FAIL2BAN=1
else
  HAS_FAIL2BAN=0
  echo "fail2ban is not available in current repositories; continuing with firewalld only."
fi

echo "[2/6] Enable Docker"
systemctl enable --now docker

echo "[3/6] Enable firewall"
systemctl enable --now firewalld
firewall-cmd --permanent --remove-service=cockpit >/dev/null 2>&1 || true
firewall-cmd --permanent --add-service=ssh
firewall-cmd --permanent --add-service=http
firewall-cmd --reload

echo "[4/6] Configure fail2ban for SSH"
if [ "$HAS_FAIL2BAN" = "1" ]; then
  cat >/etc/fail2ban/jail.d/sshd.local <<'EOF'
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/secure
maxretry = 5
findtime = 10m
bantime = 1h
EOF
  systemctl enable --now fail2ban
  systemctl restart fail2ban
else
  echo "Skip fail2ban configuration because package installation was unavailable."
fi

echo "[5/6] Prepare application directory"
mkdir -p /opt/automation-platform
chmod 755 /opt/automation-platform

echo "[6/6] Done"
echo "Next: copy or clone project into /opt/automation-platform, create .env, then run docker compose up -d --build"
