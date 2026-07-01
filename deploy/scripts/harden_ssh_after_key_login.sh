#!/usr/bin/env bash
set -euo pipefail

if [ ! -f /root/.ssh/authorized_keys ]; then
  echo "No /root/.ssh/authorized_keys found. Add and test SSH key login first."
  exit 1
fi

cat >/etc/ssh/sshd_config.d/99-automation-platform.conf <<'EOF'
PermitRootLogin prohibit-password
PasswordAuthentication no
PermitEmptyPasswords no
PubkeyAuthentication yes
MaxAuthTries 3
EOF

sshd -t
systemctl reload sshd
echo "SSH password login disabled. Keep your private key safe."
