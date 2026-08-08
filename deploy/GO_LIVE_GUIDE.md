# VoxCraft — Complete Go-Live Guide (InterServer VPS)

This walks you from **buying the VPS** to **the site live on your domain**,
in order. Follow it top to bottom — each phase assumes the previous one is
done. Nothing here touches your live Render site until Phase 10, so there's
**zero downtime risk** until you're ready to flip the switch.

**Your current site keeps working on Render the entire time** you're
setting up the VPS. If anything goes wrong along the way, nothing breaks for
your users — you just don't cut over until you're confident it works.

---

## Branch safety — read this before pushing anything

**Push all the new SQLite/deploy code to a separate branch, not `main`.**

Render auto-deploys from `main`, and Render's disk isn't persistent. If
this code reaches `main` while Render is still your live site, Render
redeploys with a brand-new **empty** database, and every real customer's
Pro key breaks — on the site actually serving traffic right now.

In GitHub's web editor: use the branch dropdown (top-left, usually says
"main") → type a new branch name like `vps-sqlite` → "Create branch". Do
all your commits (the SQLite files, deploy kit, everything from this
migration) on that branch instead. Render keeps deploying the old, working
`main` branch the entire time, completely unaffected.

You'll clone that branch specifically on the VPS (Phase 4 below), and only
merge it into `main` in **Phase 12**, after Render is fully decommissioned
and nothing is watching `main` for auto-deploy anymore.

---

## What you'll need before starting

- [ ] A card/payment method for InterServer
- [ ] Access to your Cloudflare account (DNS for voxcraft.site)
- [ ] Your GitHub repo with the latest code (all the hardening/AdSense/SQLite
      files from earlier already pushed)
- [ ] The `deploy/` folder files from earlier: `setup.sh`, `app_setup.sh`,
      `voxcraft.service`, `voxcraft-webhook.service`, `nginx-voxcraft.conf`,
      `voxcraft-deploy-sudoers`, `migrate_to_sqlite.py`, `.gitignore`
- [ ] Your existing `GITHUB_TOKEN` (needed once, for the data migration)
- [ ] Termux installed on your phone (from F-Droid, not Play Store)

---

## Phase 1 — Buy the VPS

1. Go to **interserver.net** → **VPS Hosting** (or "Cloud VPS").
2. Use their slider to configure: **1 slice** — this gives you 1 CPU core,
   2GB RAM, 30GB SSD, 1TB bandwidth. (You already decided on this size.)
3. Choose **Ubuntu** as the OS — pick **22.04 LTS** or **24.04 LTS**
   (either works with this guide; 24.04 if offered, it's newer).
4. Choose a datacenter location closest to your main audience (South
   Asia-facing traffic → a US location is usually still fine and cheapest;
   pick whatever InterServer offers closest to your users if there's a choice).
5. Complete checkout and payment.
6. **Wait for InterServer's provisioning email** — usually within a few
   minutes to an hour. It contains:
   - Your VPS's **public IP address**
   - Your **root password**
   - Possibly a control panel login (you won't need this for anything in
     this guide — everything is done via SSH)

**Save that IP address somewhere — you'll use it constantly for the next
several steps.** I'll refer to it as `YOUR_VPS_IP` throughout.

---

## Phase 2 — Point a temporary test subdomain at the VPS

Don't touch your real domain's DNS yet. Instead, create a throwaway
subdomain that points at the new VPS, so you can fully test everything
before any real traffic touches it.

1. Log into **Cloudflare** → select your `voxcraft.site` zone → **DNS**.
2. Add a new record:
   - Type: **A**
   - Name: `vps-test` (this creates `vps-test.voxcraft.site`)
   - IPv4 address: `YOUR_VPS_IP`
   - Proxy status: **DNS only (grey cloud)** — **important**, not orange/proxied

   **Why grey cloud, not orange:** if Cloudflare's proxy is on, your Nginx
   server sees Cloudflare's IP as the visitor, not the real one — and the
   whole IP-based licensing/usage-tracking system we hardened earlier relies
   on seeing the real visitor IP. Keep every VoxCraft-related DNS record
   **DNS-only** for now. (You can revisit Cloudflare's proxy/CDN features
   later once this is stable — it needs a bit more Nginx config to trust
   Cloudflare's headers correctly, which isn't covered in this guide.)

3. Save. DNS usually propagates within a few minutes with Cloudflare.
4. Test it: in Termux, `ping vps-test.voxcraft.site` — should resolve to
   `YOUR_VPS_IP`. (The ping itself may time out if InterServer blocks ICMP —
   that's fine, you just want to confirm it *resolves* to the right IP.)

---

## Phase 3 — First SSH login + OS hardening

This is `setup.sh` from your deploy kit. Full detail was covered earlier —
short version here:

```bash
# In Termux:
pkg update && pkg upgrade -y
pkg install openssh -y
ssh-keygen -t ed25519 -C "voxcraft-vps"
cat ~/.ssh/id_ed25519.pub        # copy this whole line
ssh root@YOUR_VPS_IP             # password from InterServer's email
```

Once logged in as root:
```bash
nano setup.sh     # paste the setup.sh contents
```
Edit the top two lines:
```bash
DEPLOY_USER="deploy"
SSH_PUBLIC_KEY="ssh-ed25519 AAAA...your key from above..."
```
Save (`Ctrl+O`, Enter, `Ctrl+X`), then:
```bash
bash setup.sh
```

**Before closing this root session**, open a new Termux tab and confirm:
```bash
ssh deploy@YOUR_VPS_IP
sudo whoami   # should print "root"
```
Only close the root session after that works.

---

## Phase 4 — Clone the app + build the environment

As the `deploy` user now:

```bash
ssh deploy@YOUR_VPS_IP
nano app_setup.sh     # paste contents, edit REPO_URL to your GitHub repo
                      # BRANCH is already set to "vps-sqlite" — change it
                      # here too if you named your branch something else
bash app_setup.sh
```

Fill in real secrets:
```bash
nano ~/voxcraft/.env
```
At minimum: `SECRET_KEY`, `ADMIN_PASSWORD`, `GITHUB_TOKEN` (temporary, for
the next step), `WEBHOOK_SECRET`. Generate strong values with:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Phase 5 — Bring your real data over

You have real customers in the old GitHub-JSON storage. This is the step
that makes sure they don't lose Pro access.

```bash
cd ~/voxcraft
source venv/bin/activate
python3 deploy/migrate_to_sqlite.py
```

Verify:
```bash
python3 -c "import persistence; print(len(persistence.load_license_keys()), 'keys loaded')"
```
That number should match roughly how many license keys you expect. If it
says `0` and you know you have existing customers, **stop here** and
double check `GITHUB_TOKEN` in `.env` is correct before continuing — don't
proceed to going live with empty customer data.

---

## Phase 6 — Start the app

```bash
sudo cp deploy/voxcraft.service /etc/systemd/system/voxcraft.service
sudo systemctl daemon-reload
sudo systemctl enable voxcraft
sudo systemctl start voxcraft
sudo systemctl status voxcraft
```

Should say `active (running)`. If not:
```bash
sudo journalctl -u voxcraft -n 50 --no-pager
```
Most common cause at this stage: a blank/missing value in `.env`
(`SECRET_KEY` especially — the app refuses to start without it).

Quick local check before Nginx is even involved:
```bash
curl -I http://127.0.0.1:8000
```
Should return `HTTP/1.1 200 OK` (or a redirect) — if this fails, gunicorn
itself isn't working yet, fix that before moving to Nginx.

---

## Phase 7 — Nginx + HTTPS (on the test subdomain)

```bash
sudo cp deploy/nginx-voxcraft.conf /etc/nginx/sites-available/voxcraft
sudo nano /etc/nginx/sites-available/voxcraft
```
Change `server_name yourdomain.com www.yourdomain.com;` to:
```
server_name vps-test.voxcraft.site;
```
(Just the one test subdomain for now — you'll add the real domain in Phase 10.)

```bash
sudo ln -s /etc/nginx/sites-available/voxcraft /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t                     # must say "syntax is ok"
sudo systemctl reload nginx

sudo certbot --nginx -d vps-test.voxcraft.site
```

At this point, **`https://vps-test.voxcraft.site` should load VoxCraft**,
fully separate from your live Render site.

---

## Phase 8 — Test thoroughly before going anywhere near your real domain

Go through this checklist on `https://vps-test.voxcraft.site`:

- [ ] Homepage loads, styling looks right
- [ ] Generate a short TTS clip on the free tier — works, sounds right
- [ ] Hit the free daily/monthly limit — correct block message shows
- [ ] Activate a **test** Pro license key (make a throwaway one via
      `/admin` → don't burn a real customer key) — Pro features unlock
- [ ] Try that same test key from a second browser on the same wifi —
      should also activate (the multi-browser fix from earlier)
- [ ] `/ads.txt` loads correctly (once you set `ADSENSE_PUBLISHER_ID`)
- [ ] `/admin` login works with your `ADMIN_PASSWORD`
- [ ] Admin dashboard shows your real migrated license key count
- [ ] Blog posts (if any) show up correctly
- [ ] `curl -I https://vps-test.voxcraft.site` returns `200` with a valid
      SSL cert (no browser warning)

**Don't move to Phase 9 until every box is checked.** This is the whole
point of testing on a throwaway subdomain first.

---

## Phase 9 — Set up auto-deploy (optional but recommended before cutover)

Since you edit exclusively through GitHub's web editor, do this now while
you're still on the test subdomain — easier to debug without real traffic.

```bash
sudo cp deploy/voxcraft-deploy-sudoers /etc/sudoers.d/voxcraft-deploy
sudo chmod 440 /etc/sudoers.d/voxcraft-deploy
sudo visudo -c        # MUST say the file is fine before trusting it

sudo cp deploy/voxcraft-webhook.service /etc/systemd/system/voxcraft-webhook.service
sudo systemctl daemon-reload
sudo systemctl enable voxcraft-webhook
sudo systemctl start voxcraft-webhook
```

Add to `/etc/nginx/sites-available/voxcraft`, inside the existing `server {}`
block (the one Certbot already added HTTPS to):
```nginx
    location /webhook/ {
        proxy_pass http://127.0.0.1:9001;
        proxy_set_header Host $host;
    }
```
```bash
sudo nginx -t && sudo systemctl reload nginx
```

On GitHub: repo → Settings → Webhooks → Add webhook
- Payload URL: `https://vps-test.voxcraft.site/webhook/voxcraft-deploy`
- Content type: `application/json`
- Secret: same `WEBHOOK_SECRET` as in `.env`
- Events: just "push"

Test it: edit a trivial file via GitHub's web editor, commit to your
`vps-sqlite` branch (**not main**, remember), confirm it shows up live on
the test subdomain within a few seconds.
**You'll update this webhook URL to your real domain in Phase 10, and the
branch it deploys from to `main` in Phase 12.**

---

## Phase 10 — Go live: repoint your real domain

This is the actual cutover. Do this when you're confident from Phase 8's
checklist, ideally at a low-traffic time of day.

1. **Add the real domain to Nginx first** (before touching DNS):
   ```bash
   sudo nano /etc/nginx/sites-available/voxcraft
   ```
   Change `server_name vps-test.voxcraft.site;` to include both:
   ```
   server_name voxcraft.site www.voxcraft.site;
   ```
   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   sudo certbot --nginx -d voxcraft.site -d www.voxcraft.site
   ```
   This gets the SSL cert ready **before** DNS switches, so there's no gap
   where the domain resolves to the VPS but HTTPS isn't ready yet.

2. **In Cloudflare**, edit your existing `voxcraft.site` A record (the one
   currently pointing at Render):
   - Change the IPv4 address to `YOUR_VPS_IP`
   - Keep it **DNS only (grey cloud)**, same reasoning as Phase 2
   - Do the same for the `www` record if you have one

3. **Wait for propagation** — with Cloudflare this is usually fast (a few
   minutes), but can take up to an hour depending on caching. Test with:
   ```bash
   curl -I https://voxcraft.site
   ```
   from a device on a *different* network than your VPS (to avoid any
   local DNS caching giving you a false read).

4. **Keep your Render service running for now** — don't delete or pause it
   yet. If something's wrong, you can revert the Cloudflare A record back
   to Render's IP in seconds and you're back to exactly where you started.

5. **Update the webhook URL** on GitHub (Settings → Webhooks → edit) to:
   `https://voxcraft.site/webhook/voxcraft-deploy`

6. **Update AdSense** if it's tied to the specific hosting — usually not
   necessary since the domain itself didn't change, only where it points.

---

## Phase 11 — Post-cutover checks

Repeat the Phase 8 checklist, this time on `https://voxcraft.site` (the
real domain, real traffic now flowing to it):

- [ ] Site loads correctly for a fresh visitor (test on mobile data, not
      just wifi, to rule out any local caching)
- [ ] A **real** (not test) Pro key activation works
- [ ] Ads are showing (Adsterra + AdSense, once approved)
- [ ] `/admin` shows accurate live data
- [ ] Push a real small change via GitHub web editor, confirm auto-deploy
      still works on the live domain

Give it 24–48 hours of monitoring (`sudo journalctl -u voxcraft -f` to
watch logs live, `free -h` to watch memory) before considering it fully
stable.

---

## Phase 12 — Decommission Render

Only once you're confident (a few stable days is reasonable):

1. In Render, pause or delete the VoxCraft service.
2. Cancel/downgrade the Render plan if it's a paid tier.
3. Remove any Render-specific env vars or references you no longer need.
4. **Now it's safe to merge your `vps-sqlite` branch into `main`** — in
   GitHub's web UI: open a Pull Request from `vps-sqlite` into `main`,
   review it, merge it. Nothing is watching `main` for auto-deploy anymore
   at this point, so this is just about keeping your repo's history clean
   going forward.
5. Update `voxcraft-webhook.service` on the VPS: change
   `DEPLOY_BRANCH=vps-sqlite` to `DEPLOY_BRANCH=main`, then:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart voxcraft-webhook
   ```
   Also update `app_setup.sh`'s `BRANCH` value to `main` for future reference.
   From here on, editing `main` in GitHub's web editor is what deploys.

---

## If something goes wrong

- **Site won't load after DNS switch**: revert the Cloudflare A record back
  to Render's IP immediately — you're back to normal while you debug the
  VPS separately (using `vps-test.voxcraft.site`, which still works).
- **App won't start**: `sudo journalctl -u voxcraft -n 100 --no-pager`
- **502 Bad Gateway from Nginx**: gunicorn isn't running or crashed —
  check `sudo systemctl status voxcraft`
- **Out of memory / site slow under load**: `free -h` — if swapping, drop
  `voxcraft.service` from 2 workers to 1 (edit the `ExecStart` line,
  `sudo systemctl daemon-reload && sudo systemctl restart voxcraft`)
- **License keys look wrong/missing**: check you actually ran
  `migrate_to_sqlite.py` and it reported the right key count

---

## After you're live: ongoing maintenance

- **Back up the database weekly** (it's local-only now, not synced to
  GitHub anymore):
  ```
  0 3 * * 0 cp /home/deploy/voxcraft/data/voxcraft.db /home/deploy/backups/voxcraft-$(date +\%Y\%m\%d).db
  ```
  (add via `crontab -e`, create `~/backups` first with `mkdir -p ~/backups`)
- **Code changes**: just edit in GitHub's web editor and push — auto-deploy
  handles the rest.
- **Server updates**: occasionally run `sudo apt update && sudo apt upgrade -y`
  to keep Ubuntu/Nginx/etc. patched.
