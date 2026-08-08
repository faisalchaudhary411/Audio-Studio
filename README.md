Faisal Aslam # VoxCraft — InterServer VPS Deploy Guide

Target: InterServer slice 1 (1 vCPU, 2GB RAM, 30GB SSD, Ubuntu 22.04/24.04).
Written for a mobile-only workflow (Termux + GitHub web editor, no local dev machine).

Do these steps **in order**. Each one assumes the previous one finished successfully.

---

## 0. Before you start

- [ ] InterServer VPS provisioned, you have the root IP + password from their email
- [ ] Termux installed (from F-Droid, not Play Store)
- [ ] A domain name pointed at the VPS IP (an A record) — needed for Certbot/HTTPS and the webhook
- [ ] Your VoxCraft code pushed to a GitHub repo (the hardened `app.py` / `usage_tracking.py` from the code-hardening pass should already be in it)

---

## 1. SSH key + first login (Termux, on your phone)

```bash
pkg update && pkg upgrade -y
pkg install openssh -y
ssh-keygen -t ed25519 -C "voxcraft-vps"
cat ~/.ssh/id_ed25519.pub        # copy this whole line, you'll need it in step 2
ssh root@YOUR_VPS_IP             # first login, password from InterServer's email
```

## 2. Run `setup.sh` (as root, once)

Upload `setup.sh` to the VPS (easiest: `nano setup.sh` on the VPS and paste the
contents, since you're mobile-only and this is a one-time file).

**Edit two lines at the top of the file first:**
```bash
DEPLOY_USER="deploy"
SSH_PUBLIC_KEY="ssh-ed25519 AAAA...your key from step 1..."
```

Then run it:
```bash
bash setup.sh
```

This creates the `deploy` user, locks down SSH (key-only, no root login),
enables the firewall + fail2ban, and installs Python 3.12.7, Nginx, Certbot,
git, ffmpeg, and build deps.

**Before closing this root session**, open a *new* Termux tab and confirm:
```bash
ssh deploy@YOUR_VPS_IP
sudo whoami   # should print "root"
```
Only close the root session after that works — root login is disabled after this point.

## 3. Clone the app + build the venv (as `deploy` user)

SSH in as `deploy` now (not root) and run `app_setup.sh`:

```bash
ssh deploy@YOUR_VPS_IP
nano app_setup.sh     # paste contents, edit REPO_URL to your GitHub repo
bash app_setup.sh
```

Then fill in real secrets:
```bash
nano ~/voxcraft/.env
```
At minimum: `SECRET_KEY`, `ADMIN_PASSWORD`, `GITHUB_TOKEN`, `WEBHOOK_SECRET`.
Generate strong random values with:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## 4. Migrate existing data (if you have real customers already)

If you have existing license keys, blog posts, or usage data in the old
GitHub-JSON files, migrate them into SQLite **now, before starting the
service** — otherwise the app starts with an empty database and existing
Pro customers' keys will show as invalid.

Temporarily add `GITHUB_TOKEN` to `.env` if it isn't already there (it's
only needed for this one-time read; you can remove it afterward):

```bash
python3 deploy/migrate_to_sqlite.py
```

Verify it worked:
```bash
python3 -c "import persistence; print(len(persistence.load_license_keys()), 'keys loaded')"
```

If you're starting fresh with no existing customers, skip this step — the
database is created automatically on first run with sensible defaults.

## 5. Install the gunicorn service

```bash
sudo cp deploy/voxcraft.service /etc/systemd/system/voxcraft.service
sudo systemctl daemon-reload
sudo systemctl enable voxcraft
sudo systemctl start voxcraft
sudo systemctl status voxcraft   # should say "active (running)"
```

If it fails, check logs: `sudo journalctl -u voxcraft -n 50 --no-pager`
(most likely cause: a missing/blank value in `.env` — remember `app.py` now
refuses to start without `SECRET_KEY`).

## 6. Install Nginx + HTTPS

```bash
sudo cp deploy/nginx-voxcraft.conf /etc/nginx/sites-available/voxcraft
sudo nano /etc/nginx/sites-available/voxcraft   # edit server_name to your real domain
sudo ln -s /etc/nginx/sites-available/voxcraft /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t                                    # must say "syntax is ok" before continuing
sudo systemctl reload nginx

sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Certbot edits the Nginx config in place to add HTTPS + auto-redirect from
port 80. At this point `https://yourdomain.com` should load VoxCraft.

## 7. Auto-deploy webhook (push-to-deploy from GitHub web editor)

Install the sudoers rule first — **always validate with `visudo -c` before
trusting a sudoers file**, a broken one can lock out sudo entirely:

```bash
sudo cp deploy/voxcraft-deploy-sudoers /etc/sudoers.d/voxcraft-deploy
sudo chmod 440 /etc/sudoers.d/voxcraft-deploy
sudo visudo -c
```

Install the webhook listener's service:
```bash
sudo cp deploy/voxcraft-webhook.service /etc/systemd/system/voxcraft-webhook.service
sudo systemctl daemon-reload
sudo systemctl enable voxcraft-webhook
sudo systemctl start voxcraft-webhook
sudo systemctl status voxcraft-webhook
```

Add a location block to route the webhook path through Nginx — append this
inside the existing `server { ... }` block in
`/etc/nginx/sites-available/voxcraft` (the one Certbot already added HTTPS to):

```nginx
    location /webhook/ {
        proxy_pass http://127.0.0.1:9001;
        proxy_set_header Host $host;
    }
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

**On GitHub:** repo → Settings → Webhooks → Add webhook
- Payload URL: `https://yourdomain.com/webhook/voxcraft-deploy`
- Content type: `application/json`
- Secret: the same `WEBHOOK_SECRET` value you put in `.env`
- Events: just "push"

From now on, editing a file in GitHub's web editor and committing to `main`
automatically pulls, reinstalls deps if `requirements.txt` changed, and
restarts the app — matching Render's old push-to-deploy convenience.

## 8. Sanity checks after everything is up

```bash
curl -I https://yourdomain.com                    # should be 200
sudo systemctl status voxcraft voxcraft-webhook nginx fail2ban
sudo ufw status                                     # should show 22, 80, 443 open
free -h                                             # sanity-check memory headroom
```

Push a trivial change via the GitHub web editor and confirm it shows up live
within a few seconds — that's the webhook working end to end.

---

## Notes / things worth knowing later

- **Data storage**: license keys, blog posts, usage tracking, and limits config
  live in a local SQLite database (`~/voxcraft/data/voxcraft.db`), not GitHub
  JSON — see `migrate_to_sqlite.py` if you're moving existing data over.
  **Back this file up periodically** since it's no longer implicitly synced
  to GitHub on every write. A simple weekly cron is enough for this scale:
  ```
  0 3 * * 0 cp /home/deploy/voxcraft/data/voxcraft.db /home/deploy/backups/voxcraft-$(date +\%Y\%m\%d).db
  ```
- **Memory budget**: gunicorn is configured for 2 workers with `--preload`
  (~358MB/worker post warm-up, shared library pages via copy-on-write). That's
  workable but not generous on a 2GB box — keep an eye on `free -h` under real
  load, and drop to 1 worker in `voxcraft.service` if you see swapping.
- **IP-based usage limits and Freemius/licensing logic depend on Nginx setting
  `X-Real-IP` correctly** (see `nginx-voxcraft.conf`). If you ever swap
  reverse proxies, that header must be preserved or usage tracking breaks.
- **The webhook listener can only run one exact command as root** — restarting
  the voxcraft service — nothing else. That scope is enforced by the sudoers
  file, not just by the Python code.
- `.env` is gitignored — it never leaves the VPS. If you rotate any secret,
  edit it directly on the server and `sudo systemctl restart voxcraft` (and
  `voxcraft-webhook` if `WEBHOOK_SECRET` changed).
