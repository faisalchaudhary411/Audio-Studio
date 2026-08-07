#!/usr/bin/env bash
#
# setup.sh — VoxCraft VPS provisioning (InterServer slice 1: 1 vCPU, 2GB RAM, 30GB SSD)
#
# Run ONCE as root on a fresh Ubuntu 22.04/24.04 VPS, right after first login:
#   bash setup.sh
#
# What this does:
#   1. OS hardening — creates a non-root sudo user, sets up SSH key auth,
#      disables root SSH login and password auth, enables ufw firewall + fail2ban
#   2. Installs Python 3.12.7 (matches your Render pin), Nginx, Certbot, git,
#      ffmpeg, and the build headers lameenc/librosa/soundfile need
#   3. Leaves the box ready for: git clone, venv, gunicorn systemd service,
#      nginx reverse proxy, webhook auto-deploy listener (separate steps)
#
# After this script finishes, you MUST log out and log back in as the new
# user (not root) — root password/SSH login will be disabled.

set -euo pipefail

# ---------------------------------------------------------------------------
# 0. Config — EDIT THESE before running
# ---------------------------------------------------------------------------
DEPLOY_USER="deploy"
SSH_PUBLIC_KEY=""   # paste the output of `cat ~/.ssh/id_ed25519.pub` from Termux here

if [[ -z "$SSH_PUBLIC_KEY" ]]; then
    echo "ERROR: SSH_PUBLIC_KEY is empty. Edit setup.sh and paste your public key"
    echo "       (from Termux: cat ~/.ssh/id_ed25519.pub) before running this."
    exit 1
fi

if [[ "$EUID" -ne 0 ]]; then
    echo "ERROR: run this as root (first login only)."
    exit 1
fi

echo "=== 1/6: Creating non-root sudo user: $DEPLOY_USER ==="
if id "$DEPLOY_USER" &>/dev/null; then
    echo "User $DEPLOY_USER already exists, skipping creation."
else
    adduser --disabled-password --gecos "" "$DEPLOY_USER"
    usermod -aG sudo "$DEPLOY_USER"
fi

mkdir -p /home/"$DEPLOY_USER"/.ssh
echo "$SSH_PUBLIC_KEY" > /home/"$DEPLOY_USER"/.ssh/authorized_keys
chmod 700 /home/"$DEPLOY_USER"/.ssh
chmod 600 /home/"$DEPLOY_USER"/.ssh/authorized_keys
chown -R "$DEPLOY_USER":"$DEPLOY_USER" /home/"$DEPLOY_USER"/.ssh

echo "=== 2/6: Hardening SSH (key-only, no root login) ==="
SSHD_CONFIG="/etc/ssh/sshd_config"
cp "$SSHD_CONFIG" "${SSHD_CONFIG}.bak.$(date +%s)"

# Use a drop-in file instead of editing sshd_config directly — safer to
# reason about and easy to undo by deleting the file.
mkdir -p /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/99-voxcraft-hardening.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
ChallengeResponseAuthentication no
UsePAM yes
EOF

echo "=== 3/6: Firewall (ufw) ==="
apt-get update -y
apt-get install -y ufw
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "=== 4/6: fail2ban (SSH brute-force protection) ==="
apt-get install -y fail2ban
cat > /etc/fail2ban/jail.local <<'EOF'
[sshd]
enabled = true
maxretry = 5
bantime = 3600
findtime = 600
EOF
systemctl enable fail2ban
systemctl restart fail2ban

echo "=== 5/6: Installing Python 3.12.7, Nginx, Certbot, git, ffmpeg, build deps ==="
apt-get install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update -y
apt-get install -y \
    python3.12 python3.12-venv python3.12-dev \
    nginx \
    certbot python3-certbot-nginx \
    git \
    ffmpeg \
    build-essential libffi-dev libssl-dev \
    libsndfile1

echo "=== 6/6: Restarting SSH with hardened config ==="
sshd -t   # validate config before restarting — abort if broken
systemctl restart ssh

echo ""
echo "============================================================"
echo " Done. IMPORTANT — before you close this session:"
echo "  1. Open a NEW Termux tab and test:"
echo "       ssh $DEPLOY_USER@<your-vps-ip>"
echo "  2. Confirm you can log in AND run: sudo whoami  (should print 'root')"
echo "  3. Only after that works, close this root session."
echo "     Root SSH login and password auth are now disabled."
echo "============================================================"
