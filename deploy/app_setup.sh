#!/usr/bin/env bash
#
# app_setup.sh — clones VoxCraft and builds its venv.
# Run as the DEPLOY user (not root) after setup.sh + re-login:
#   bash app_setup.sh
#
# Edit REPO_URL below to your actual GitHub repo first.

set -euo pipefail

REPO_URL="https://github.com/YOUR_GITHUB_USERNAME/Audio-Studio.git"   # EDIT THIS
APP_DIR="$HOME/voxcraft"

if [[ "$REPO_URL" == *"YOUR_GITHUB_USERNAME"* ]]; then
    echo "ERROR: edit app_setup.sh and set REPO_URL to your actual repo first."
    exit 1
fi

echo "=== Cloning repo ==="
if [[ -d "$APP_DIR" ]]; then
    echo "$APP_DIR already exists — pulling latest instead of cloning."
    cd "$APP_DIR" && git pull
else
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

echo "=== Creating venv (Python 3.12) ==="
python3.12 -m venv venv
source venv/bin/activate

echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn==22.0.0   # already in requirements.txt, kept here as a safety net

echo "=== Creating .env template (fill in real values before starting the service) ==="
if [[ ! -f "$APP_DIR/.env" ]]; then
    cat > "$APP_DIR/.env" <<'EOF'
# VoxCraft production environment variables.
# This file is loaded by systemd (EnvironmentFile=) — NOT committed to git.
# Generate SECRET_KEY with: python3 -c "import secrets; print(secrets.token_hex(32))"

SECRET_KEY=
ADMIN_PASSWORD=
GITHUB_TOKEN=
RESEND_API_KEY=
ADMIN_EMAIL=
FREEMIUS_API_TOKEN=
FREEMIUS_PRODUCT_ID=
PORT=8000

# Shared secret for the GitHub webhook auto-deploy listener. Generate with:
#   python3 -c "import secrets; print(secrets.token_hex(32))"
# Paste the SAME value into GitHub repo Settings -> Webhooks -> Secret.
WEBHOOK_SECRET=
EOF
    chmod 600 "$APP_DIR/.env"
    echo "Created $APP_DIR/.env — EDIT IT NOW and fill in real secret values."
else
    echo "$APP_DIR/.env already exists, leaving it alone."
fi

echo ""
echo "============================================================"
echo " Done. Next steps:"
echo "  1. nano $APP_DIR/.env   — fill in SECRET_KEY, ADMIN_PASSWORD, etc."
echo "  2. Install the systemd services (voxcraft.service, nginx config)"
echo "  3. sudo systemctl start voxcraft"
echo "============================================================"
