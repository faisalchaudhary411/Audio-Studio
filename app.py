"""
VoxCraft — Flask app.

This pass: real licensing (internal keys + Freemius), IP-based usage tracking,
manual pro-request queue, admin panel, ads, blog, and privacy/terms/contact
pages — ported from your Streamlit app's backend modules (see persistence.py,
licensing.py, usage_tracking.py, notifications.py, pro_requests.py).

Still NOT ported: Music tool, Denoise, Voice Changer, Video-to-Audio extractor.
Paddle is intentionally NOT ported (Freemius replaced it per your own history).

REQUIRED ENV VARS for this pass to actually work (see README):
- SECRET_KEY        — Flask session signing key (app refuses to start without it)
- ADMIN_PASSWORD    — gates /admin (there was NO auth on the original admin page — added here)
- RESEND_API_KEY, ADMIN_EMAIL — for pro-request notification emails
- FREEMIUS_API_TOKEN, FREEMIUS_PRODUCT_ID — only if you want Freemius checkout wired live

GITHUB_TOKEN is no longer needed — persistence.py moved from GitHub-JSON to
a local SQLite database (see persistence.py's docstring and
deploy/migrate_to_sqlite.py if migrating existing data over).
"""

from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for, flash, Response
import os
import io
import time
import threading
import zipfile
import base64
import secrets
import datetime as dt
import markdown as md_lib

from voices import VOICES, FREE_VOICES, default_preview_text
from tts_engine import tts_dispatch
from clone_engine import start_clone_job, get_job
import music_engine
import audio_tools
import persistence
import licensing
import usage_tracking
import pro_requests
import notifications
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import hmac

CLONE_UPLOAD_DIR = "/tmp/voxcraft_clone_refs"
os.makedirs(CLONE_UPLOAD_DIR, exist_ok=True)
CLONE_CHAR_LIMIT = 500  # tighter than normal TTS — keeps CPU generation time bounded

app = Flask(__name__)

# HARDENING: no insecure fallback secret. A hardcoded SECRET_KEY means anyone
# can forge a session cookie — including admin_authed=True, which bypasses
# /admin login entirely. Fail loudly at startup instead of silently running
# with a public, guessable key. Set SECRET_KEY as a real env var on the VPS
# (e.g. `python3 -c "import secrets; print(secrets.token_hex(32))"`).
_secret_key = os.environ.get("SECRET_KEY", "")
if not _secret_key:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set. Refusing to start with "
        "an insecure default — set SECRET_KEY before running the app."
    )
app.secret_key = _secret_key

# HARDENING: on the VPS, Flask sits behind Nginx as a reverse proxy. Without
# ProxyFix, Flask doesn't know the original request was HTTPS or came from
# the real client, which breaks secure cookies and url_for(..., _external=True).
# x_for/x_proto/x_host=1 means "trust exactly one hop" — i.e. trust Nginx,
# and only Nginx, to set these headers accurately (Nginx overwrites rather
# than blindly forwards client-supplied values — see deploy notes).
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# HARDENING: cap request body size globally (50 MB) so a single huge upload
# (clone reference audio, tool file uploads) can't exhaust RAM/disk on a
# single-worker VPS process — the same class of bug as the WealthThroughAges
# OOM crash. Nginx should also set client_max_body_size to match (see notes).
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

# HARDENING: explicit session cookie flags. SECURE requires the app to only
# ever be reached over HTTPS (true once Nginx+certbot is set up) — browsers
# will simply refuse to send the cookie over plain HTTP, which is fine since
# Nginx will redirect http->https anyway.
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# BUG FIX (critical): sessions were never made permanent, so Flask's default
# session cookie had NO explicit expiry at all — a true browser "session"
# cookie, meant to last only until the browser fully closes. On mobile,
# Android (and iOS) routinely kill backgrounded browser tabs/apps to save
# memory/battery — very commonly overnight while the phone charges — which
# clears exactly this kind of cookie. That matches the "Pro resets around
# midnight" symptom far better than anything server-side/date-based, since
# there's no actual date-based reset logic touching license_key anywhere in
# this file. Making sessions permanent with an explicit long lifetime means
# the cookie gets a real expiry date, so it survives the browser/OS clearing
# out non-permanent session-scoped cookies.
app.config["PERMANENT_SESSION_LIFETIME"] = dt.timedelta(days=90)


@app.before_request
def _make_session_permanent():
    session.permanent = True


@app.before_request
def _ensure_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)


@app.before_request
def _csrf_protect():
    """Rejects any POST that doesn't carry a matching csrf_token — closes
    the classic CSRF hole where a malicious page tricks a logged-in admin's
    browser into submitting a hidden form to voxcraft.site. SameSite=Lax on
    the session cookie already blocks most of this on modern browsers, but
    that's a browser behavior we're relying on rather than something the
    app itself enforces — this makes it explicit and doesn't depend on
    every visitor's browser getting SameSite right.

    Scoped to real HTML forms (admin pages, /activate, /upgrade,
    /fs-callback/activate) — NOT /api/* or /webhook/*. The /api/ tool
    endpoints are called via JS fetch(), not a <form>, and adding tokens
    there would mean also updating every JS file that calls them for
    comparatively low value (worst case is someone tricking a visitor into
    submitting an unwanted TTS generation, not an account/data compromise).
    /webhook/* uses its own HMAC signature verification instead, which is
    the correct mechanism for a server-to-server call with no session/
    cookie involved at all."""
    if request.method != "POST":
        return
    exempt_prefixes = ("/webhook/", "/api/")
    if request.path.startswith(exempt_prefixes):
        return
    token = session.get("csrf_token", "")
    submitted = request.form.get("csrf_token", "")
    if not token or not submitted or not hmac.compare_digest(token, submitted):
        return jsonify({"error": "Your session expired or the page was open too long. Please refresh and try again."}), 403


@app.before_request
def _auto_restore_pro_session():
    """If this browser has no license_key in session (cookies cleared,
    incognito, or a different browser than where they activated), silently
    check whether this device's IP or fingerprint matches an already-active
    key's history and restore it — see licensing.find_key_for_device() for
    the deliberate convenience-vs-shared-network trade-off this makes.
    Skipped for static assets and webhook/health endpoints, which never
    need Pro status and would otherwise trigger a needless DB scan on
    every single request (image, CSS, JS file, etc.)."""
    if session.get("license_key"):
        return
    skip_prefixes = ("/static/", "/webhook/", "/ads.txt")
    if request.path.startswith(skip_prefixes):
        return
    restored_key = licensing.find_key_for_device(request)
    if restored_key:
        session["license_key"] = restored_key

# librosa's pitch_shift uses numba, which JIT-compiles on first call —
# ~20s the very first time, milliseconds after. Warming it up here (module
# level, so this runs under gunicorn too, not just `python app.py` directly)
# means the first real Voice Changer user doesn't eat that cost.
def _warm_up_librosa():
    try:
        import numpy as _np
        import librosa as _librosa
        _librosa.effects.pitch_shift(_np.zeros(2048, dtype=_np.float32), sr=22050, n_steps=1)
    except Exception:
        pass  # non-fatal — worst case, the first real request just pays the JIT cost instead


threading.Thread(target=_warm_up_librosa, daemon=True).start()

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()

# Limits now come from persistence.load_limits() (GitHub-backed, editable in
# /admin/limits) instead of hardcoded constants. Cached briefly so we're not
# hitting the GitHub API on every single request — admin changes take effect
# within LIMITS_CACHE_TTL seconds, not instantly, which is a fine trade-off.
LIMITS_CACHE_TTL = 30
_limits_cache = {"data": None, "ts": 0}


def get_limits() -> dict:
    now = time.time()
    if _limits_cache["data"] is None or (now - _limits_cache["ts"]) > LIMITS_CACHE_TTL:
        _limits_cache["data"] = persistence.load_limits()
        _limits_cache["ts"] = now
    return _limits_cache["data"]


def is_pro() -> bool:
    """Real check now: validates the license key stored in this session
    against licensing.check_vox_license() (backed by license_keys.json on
    GitHub). Falls back to False if no key is activated or GITHUB_TOKEN
    isn't configured yet."""
    key = session.get("license_key")
    if not key:
        return False
    return licensing.check_vox_license(key).get("valid", False)


def admin_required(view_func):
    from functools import wraps

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_authed"):
            return redirect(url_for("admin_login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapper


@app.context_processor
def inject_globals():
    return {
        "is_pro_ctx": is_pro(),
        "google_site_verification_code": os.environ.get("GOOGLE_SITE_VERIFICATION", ""),
        "adsense_publisher_id": os.environ.get("ADSENSE_PUBLISHER_ID", ""),
        # Popunder is OFF by default — deliberately paused while AdSense
        # reviews the site (popunders are on Google/Coalition for Better Ads'
        # disallowed list; running one during review risks rejection). Set
        # ENABLE_POPUNDER=1 in Render's env vars to switch it back on after
        # approval — no code change or redeploy needed beyond the env var.
        "enable_popunder_ctx": os.environ.get("ENABLE_POPUNDER", "") == "1",
        "csrf_token": session.get("csrf_token", ""),
    }


def _today() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d")


def _this_month() -> str:
    return dt.datetime.now().strftime("%Y-%m")


def _under_limit(counter_key: str, limit: int) -> bool:
    """Read-only check — does NOT increment. Use this before doing the actual
    work, then call _bump_counter only if it succeeds.
    Backed by usage_tracking.py's combined IP+fingerprint store — see that
    module's docstring for why this replaced pure session-cookie tracking
    (which any free user could reset via private browsing or a different
    browser, no code exploit needed, just normal browser features)."""
    if is_pro():
        return True
    return usage_tracking.get_daily_counter(request, counter_key) < limit


def _bump_counter(counter_key: str):
    """Only call this AFTER the operation actually succeeds."""
    if is_pro():
        return
    usage_tracking.bump_daily_counter(request, counter_key)


def _check_and_bump(counter_key: str, limit: int) -> bool:
    """Returns True if under limit (and increments), False if limit hit."""
    if is_pro():
        return True
    if not _under_limit(counter_key, limit):
        return False
    _bump_counter(counter_key)
    return True


def _monthly_chars_used() -> int:
    return usage_tracking.get_monthly_chars(request)


def _would_exceed_monthly_quota(char_count: int, monthly_quota: int) -> bool:
    """Read-only check — does NOT bump the counter. Used before generating,
    so a failed generation (e.g. TTS engine error) never consumes quota."""
    if is_pro():
        return False
    return _monthly_chars_used() + char_count > monthly_quota


def _bump_monthly_chars(char_count: int):
    """Only call this AFTER a generation actually succeeds."""
    if is_pro():
        return
    usage_tracking.bump_monthly_chars(request, char_count)


@app.route("/")
def landing():
    # Curated, real subset for the homepage voice library — South Asian
    # languages featured prominently per the differentiation strategy.
    # audio_slug matches the predictable /static/audio/previews/<slug>.mp3
    # naming convention the preview player (main.js initVoicePreviews)
    # expects — missing files degrade gracefully rather than erroring.
    featured_voices = [
        {"name": "Uzma", "gender": "Female", "language": "Urdu", "voice_id": "ur-PK-UzmaNeural"},
        {"name": "Asad", "gender": "Male", "language": "Urdu", "voice_id": "ur-PK-AsadNeural"},
        {"name": "Swara", "gender": "Female", "language": "Hindi", "voice_id": "hi-IN-SwaraNeural"},
        {"name": "Tanishaa", "gender": "Female", "language": "Bengali", "voice_id": "bn-IN-TanishaaNeural"},
        {"name": "Vaani", "gender": "Female", "language": "Punjabi", "voice_id": "pa-IN-VaaniNeural"},
        {"name": "Pallavi", "gender": "Female", "language": "Tamil", "voice_id": "ta-IN-PallaviNeural"},
        {"name": "Shruti", "gender": "Female", "language": "Telugu", "voice_id": "te-IN-ShrutiNeural"},
        {"name": "Jenny", "gender": "Female", "language": "US English", "voice_id": "en-US-JennyNeural"},
        {"name": "Ryan", "gender": "Male", "language": "UK English", "voice_id": "en-GB-RyanNeural"},
        {"name": "Zariyah", "gender": "Female", "language": "Arabic", "voice_id": "ar-SA-ZariyahNeural"},
        {"name": "Henri", "gender": "Male", "language": "French", "voice_id": "fr-FR-HenriNeural"},
        {"name": "Xiaoxiao", "gender": "Female", "language": "Chinese (Mandarin)", "voice_id": "zh-CN-XiaoxiaoNeural"},
    ]
    for v in featured_voices:
        v["audio_slug"] = v["voice_id"].lower()

    all_posts = persistence.load_blogs()
    recent_posts = [p for p in all_posts if p.get("published")][:3]

    return render_template("landing.html", featured_voices=featured_voices, recent_posts=recent_posts)


def usage_summary() -> dict:
    """Surfaces the SAME counters that _under_limit / _monthly_chars_used
    actually enforce — now backed by usage_tracking.py's combined
    IP+fingerprint store, so what's displayed always matches what's
    enforced (this used to read session values while enforcement quietly
    ran on something else entirely — see usage_tracking.py's docstring for
    the full history). Limits themselves come from get_limits() (editable
    in /admin/limits)."""
    lim = get_limits()
    return {
        "singles": {"used": usage_tracking.get_daily_counter(request, "usage_singles"), "limit": lim["FREE_DAILY_ACTIONS"]},
        "chars_monthly": {"used": _monthly_chars_used(), "limit": lim["FREE_MONTHLY_CHAR_QUOTA"]},
        "batches": {"used": usage_tracking.get_daily_counter(request, "usage_batches"), "limit": lim["FREE_BATCH_LIMIT"]},
        "previews": {"used": usage_tracking.get_daily_counter(request, "usage_previews"), "limit": lim["FREE_PREVIEW_LIMIT"]},
        "transcribe": {"used": usage_tracking.get_daily_counter(request, "usage_transcribe"), "limit": lim["FREE_DAILY_ACTIONS"]},
        "convert": {"used": usage_tracking.get_daily_counter(request, "usage_convert"), "limit": lim["FREE_DAILY_ACTIONS"]},
        "merge": {"used": usage_tracking.get_daily_counter(request, "usage_merge"), "limit": lim["FREE_DAILY_ACTIONS"]},
        "cutter": {"used": usage_tracking.get_daily_counter(request, "usage_cutter"), "limit": lim["FREE_DAILY_ACTIONS"]},
        "denoise": {"used": usage_tracking.get_daily_counter(request, "usage_denoise"), "limit": lim["FREE_DAILY_ACTIONS"]},
        "voicechange": {"used": usage_tracking.get_daily_counter(request, "usage_voicechange"), "limit": lim["FREE_DAILY_ACTIONS"]},
        "videoxtract": {"used": usage_tracking.get_daily_counter(request, "usage_videoxtract"), "limit": lim["FREE_DAILY_ACTIONS"]},
    }


@app.route("/studio")
def studio():
    lim = get_limits()
    active_voices = VOICES if is_pro() else FREE_VOICES
    return render_template("studio.html", voices=active_voices, pro=is_pro(),
                            free_char_limit=lim["FREE_CHAR_LIMIT"], batch_max=lim["FREE_BATCH_MAX_LINES"],
                            monthly_char_quota=lim["FREE_MONTHLY_CHAR_QUOTA"],
                            usage=usage_summary())


@app.route("/pricing")
def pricing():
    limits = persistence.load_limits()
    free_features = [f.strip() for f in (limits.get("FREE_FEATURES") or "").split("|") if f.strip()] or [
        f"{limits['FREE_DAILY_ACTIONS']} generations/day",
        f"{limits['FREE_CHAR_LIMIT']:,} chars/generation",
        f"{limits['FREE_VOICES_COUNT']} voices",
        "Ads supported",
    ]
    pro_features = [f.strip() for f in (limits.get("PRO_FEATURES") or "").split("|") if f.strip()] or [
        "Unlimited generations", "Unlimited characters", "All voices, all languages",
        "No ads", f"Batch up to {limits['PRO_BATCH_MAX']} lines", "Voice cloning (where enabled)",
    ]
    plans = [
        {"id": "free", "name": "Free", "price": limits.get("FREE_PRICE_LABEL", "$0"), "period": "forever",
         "limits": free_features, "cta": "Current plan", "cta_url": None},
        {"id": "pro", "name": "Pro", "price": limits.get("PRO_PRICE_LABEL", "840 PKR"), "period": "/month",
         "limits": pro_features, "cta": "Get Pro", "featured": True,
         "cta_url": url_for("upgrade")},
    ]
    return render_template("pricing.html", plans=plans)


# ---------------------------------------------------------------------------
# Licensing: activate a key, submit a manual pro request
# ---------------------------------------------------------------------------
@app.route("/activate", methods=["GET", "POST"])
def activate():
    if request.method == "GET":
        return render_template("activate.html")
    key = (request.form.get("license_key") or "").strip()
    if not key:
        return render_template("activate.html", error="Enter a license key.")
    result = licensing.activate_any_license(key, request)
    if result.get("valid"):
        # Store the INTERNAL key in the session (not whatever the customer typed —
        # if they entered a Freemius key, result["internal_key"] is the wrapper key
        # that everything else in the app checks against).
        session["license_key"] = result.get("internal_key", key)
        return render_template("activate.html", success=True, name=result.get("name"))
    return render_template("activate.html", error=result.get("error", "Invalid license key."))


@app.route("/upgrade", methods=["GET", "POST"])
def upgrade():
    checkout_url = persistence.load_limits().get("CHECKOUT_URL") or None
    if request.method == "GET":
        # BUG FIX: this previously never read MANUAL_GRACE_HOURS at all on
        # the initial page load — only after submitting the form — so the
        # "access stops working after X hours" text was disconnected from
        # whatever was actually set in /admin/limits.
        grace_hours = persistence.load_limits().get("MANUAL_GRACE_HOURS", 72)
        return render_template("upgrade.html", checkout_url=checkout_url, grace_hours=grace_hours)
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    payment_method = (request.form.get("payment_method") or "").strip()
    txn_id = (request.form.get("txn_id") or "").strip()
    if not name or not email:
        return render_template("upgrade.html", error="Name and email are required.", checkout_url=checkout_url)

    screenshot_b64 = ""
    file = request.files.get("screenshot")
    if file and file.filename:
        screenshot_b64 = base64.b64encode(file.read()).decode("ascii")

    # BUG FIX: check Pro status BEFORE processing the submission. Without
    # this, submitting a second payment request while already Pro (e.g. an
    # early renewal attempt, or just clicking submit twice) would
    # unconditionally overwrite the session's license_key with a brand-new
    # TEMPORARY grace key — silently swapping a permanent, already-valid key
    # for one on a 24-hour countdown. Combined with sweep_expired_keys(),
    # that meant a genuinely paying customer could lose Pro access after the
    # grace window, even though their real key was never actually invalid.
    already_pro = is_pro()

    result = pro_requests.submit_pro_request(request, name, email, phone, payment_method, txn_id, screenshot_b64)
    if result.get("success"):
        if result.get("auto_approved") and result.get("license_key") and not already_pro:
            session["license_key"] = result["license_key"]  # instant unlock on this device
        return render_template("upgrade.html", submitted=True, req_id=result["id"], checkout_url=checkout_url,
                                auto_approved=result.get("auto_approved", False),
                                grace_hours=result.get("grace_hours"),
                                already_pro=already_pro)
    return render_template("upgrade.html", error=result.get("error", "Something went wrong. Please try again."), checkout_url=checkout_url)


# ---------------------------------------------------------------------------
# Blog (public)
# ---------------------------------------------------------------------------
@app.route("/blog")
def blog_list():
    posts = [p for p in persistence.load_blogs() if p.get("published")]
    posts.sort(key=lambda p: p.get("date", ""), reverse=True)
    return render_template("blog_list.html", posts=posts)


@app.route("/blog/<post_id>")
def blog_detail(post_id):
    posts = persistence.load_blogs()
    post = next((p for p in posts if str(p.get("id")) == str(post_id) and p.get("published")), None)
    if not post:
        return render_template("blog_list.html", posts=[], not_found=True), 404
    post_html = md_lib.markdown(post.get("body", ""))
    return render_template("blog_detail.html", post=post, post_html=post_html)


# ---------------------------------------------------------------------------
# Static content pages
# ---------------------------------------------------------------------------
@app.route("/sitemap.xml")
def sitemap():
    """Dynamically generated — includes every public page plus every
    published blog post, using whatever domain the request actually came in
    on (so it's correct whether you're on Render's default domain or your
    real one, without needing a hardcoded base URL)."""
    base = request.url_root.rstrip("/")
    static_paths = [
        ("/", "1.0", "weekly"),
        ("/studio", "0.9", "weekly"),
        ("/tools", "0.9", "weekly"),
        ("/pricing", "0.8", "monthly"),
        ("/blog", "0.7", "weekly"),
        ("/upgrade", "0.6", "monthly"),
        ("/activate", "0.5", "monthly"),
        ("/privacy", "0.3", "yearly"),
        ("/terms", "0.3", "yearly"),
        ("/contact", "0.4", "yearly"),
    ]
    urls = [{"loc": f"{base}{path}", "priority": priority, "changefreq": freq}
            for path, priority, freq in static_paths]

    for post in persistence.load_blogs():
        if post.get("published"):
            urls.append({
                "loc": f"{base}/blog/{post.get('id')}",
                "priority": "0.6",
                "changefreq": "monthly",
                "lastmod": post.get("date", ""),
            })

    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml_parts.append("  <url>")
        xml_parts.append(f"    <loc>{u['loc']}</loc>")
        if u.get("lastmod"):
            xml_parts.append(f"    <lastmod>{u['lastmod']}</lastmod>")
        xml_parts.append(f"    <changefreq>{u['changefreq']}</changefreq>")
        xml_parts.append(f"    <priority>{u['priority']}</priority>")
        xml_parts.append("  </url>")
    xml_parts.append("</urlset>")

    return app.response_class("\n".join(xml_parts), mimetype="application/xml")


@app.route("/robots.txt")
def robots_txt():
    base = request.url_root.rstrip("/")
    content = f"""User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/

Sitemap: {base}/sitemap.xml
"""
    return app.response_class(content, mimetype="text/plain")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------
ADMIN_LOGIN_MAX_ATTEMPTS = 5
ADMIN_LOGIN_WINDOW_MINUTES = 15
ADMIN_LOGIN_LOCKOUT_MINUTES = 15


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin/login.html")

    ip_hash = usage_tracking.hash_ip(usage_tracking.get_client_ip(request))
    now = dt.datetime.now()
    record = persistence.get_login_attempts(ip_hash)

    # Currently locked out? Reject before even checking the password —
    # otherwise a correct guess during lockout would still let an attacker
    # in, defeating the point of the lockout.
    locked_until_str = record.get("locked_until")
    if locked_until_str:
        locked_until = dt.datetime.strptime(locked_until_str, "%Y-%m-%d %H:%M:%S")
        if now < locked_until:
            remaining_min = max(1, int((locked_until - now).total_seconds() // 60) + 1)
            return render_template("admin/login.html",
                                    error=f"Too many failed attempts. Try again in {remaining_min} minute(s).")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    # HARDENING: constant-time comparison instead of == — plain string
    # comparison short-circuits on the first mismatched character, which
    # theoretically leaks timing info about the correct value. hmac.compare_digest
    # runs in constant time regardless of where the strings first differ.
    # Both email AND password must match — reusing ADMIN_EMAIL (already set
    # for pro-request notifications) means logging in now takes two secrets
    # instead of one, not just a cosmetic field.
    email_ok = bool(ADMIN_EMAIL) and hmac.compare_digest(email, ADMIN_EMAIL)
    password_ok = bool(ADMIN_PASSWORD) and hmac.compare_digest(password, ADMIN_PASSWORD)
    if email_ok and password_ok:
        persistence.clear_login_attempts(ip_hash)  # legitimate login wipes any prior failed attempts
        session["admin_authed"] = True
        next_url = request.args.get("next") or url_for("admin_dashboard")
        return redirect(next_url)

    # Wrong email or password (deliberately not saying which, so a wrong
    # guess can't be used to enumerate the correct email separately from
    # the correct password) — record the attempt. Stored in the DB (not an
    # in-memory dict) because gunicorn runs multiple worker processes; an
    # in-memory counter would only apply per-worker, silently doubling the
    # effective attempt budget an attacker gets depending on which worker
    # handles each request.
    first_attempt_str = record.get("first_attempt")
    if first_attempt_str:
        first_attempt = dt.datetime.strptime(first_attempt_str, "%Y-%m-%d %H:%M:%S")
        if (now - first_attempt).total_seconds() > ADMIN_LOGIN_WINDOW_MINUTES * 60:
            record = {}  # window expired — start counting fresh

    count = record.get("count", 0) + 1
    new_record = {
        "count": count,
        "first_attempt": record.get("first_attempt", now.strftime("%Y-%m-%d %H:%M:%S")),
    }
    if count >= ADMIN_LOGIN_MAX_ATTEMPTS:
        new_record["locked_until"] = (now + dt.timedelta(minutes=ADMIN_LOGIN_LOCKOUT_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    persistence.set_login_attempts(ip_hash, new_record)

    if count >= ADMIN_LOGIN_MAX_ATTEMPTS:
        return render_template("admin/login.html",
                                error=f"Too many failed attempts. Try again in {ADMIN_LOGIN_LOCKOUT_MINUTES} minutes.")
    return render_template("admin/login.html", error="Incorrect email or password.")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_authed", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    licensing.sweep_expired_keys()  # mark any newly-expired keys as revoked before counting
    keys = persistence.load_license_keys()
    reqs = persistence.load_requests()
    posts = persistence.load_blogs()
    active_keys = sum(1 for k, v in keys.items() if licensing.is_subscription_active(v) and not v.get("revoked"))
    pending_reqs = sum(1 for r in reqs if r.get("status") in ("pending", "payment_pending"))
    anns = persistence.load_announcements()
    live_anns = sum(1 for a in anns if a.get("active"))
    return render_template("admin/dashboard.html",
                            total_keys=len(keys), active_keys=active_keys,
                            pending_reqs=pending_reqs, total_posts=len(posts),
                            total_anns=len(anns), live_anns=live_anns,
                            db_path=persistence.DB_PATH)


@app.route("/admin/limits", methods=["GET", "POST"])
@admin_required
def admin_limits():
    if request.method == "POST":
        limits = {
            "FREE_CHAR_LIMIT": int(request.form.get("FREE_CHAR_LIMIT", 5000)),
            "FREE_MONTHLY_CHAR_QUOTA": int(request.form.get("FREE_MONTHLY_CHAR_QUOTA", 50000)),
            "FREE_DAILY_ACTIONS": int(request.form.get("FREE_DAILY_ACTIONS", 10)),
            "FREE_BATCH_LIMIT": int(request.form.get("FREE_BATCH_LIMIT", 5)),
            "FREE_BATCH_MAX_LINES": int(request.form.get("FREE_BATCH_MAX_LINES", 20)),
            "FREE_PREVIEW_LIMIT": int(request.form.get("FREE_PREVIEW_LIMIT", 5)),
            "PRO_BATCH_MAX": int(request.form.get("PRO_BATCH_MAX", 20)),
            "FREE_VOICES_COUNT": int(request.form.get("FREE_VOICES_COUNT", 20)),
            "PRO_PRICE_PKR": int(request.form.get("PRO_PRICE_PKR", 840)),
            "PRO_PRICE_LABEL": request.form.get("PRO_PRICE_LABEL", "840 PKR"),
            "FREE_PRICE_LABEL": request.form.get("FREE_PRICE_LABEL", "$0"),
            "CHECKOUT_URL": request.form.get("CHECKOUT_URL", ""),
            "FREE_FEATURES": request.form.get("FREE_FEATURES", ""),
            "PRO_FEATURES": request.form.get("PRO_FEATURES", ""),
            "AUTO_APPROVE_MANUAL": request.form.get("AUTO_APPROVE_MANUAL") == "on",
            "MANUAL_GRACE_HOURS": int(request.form.get("MANUAL_GRACE_HOURS", 72)),
        }
        ok, err = persistence.save_limits(limits)
        _limits_cache["data"] = None  # force refresh so the change is visible immediately, not after LIMITS_CACHE_TTL
        return render_template("admin/limits.html", limits=limits, saved=ok, error=err)
    limits = persistence.load_limits()
    return render_template("admin/limits.html", limits=limits)


@app.route("/admin/keys", methods=["GET", "POST"])
@admin_required
def admin_keys():
    if request.method == "POST":
        action = request.form.get("action")
        key = request.form.get("key", "")
        if action == "create":
            licensing.create_new_key_manual()
        elif action == "revoke":
            licensing.revoke_key(key)
        elif action == "unrevoke":
            licensing.unrevoke_key(key)
        elif action == "delete":
            licensing.delete_key(key)
        elif action == "reset_device":
            licensing.reset_device_lock(key)
        return redirect(url_for("admin_keys"))
    licensing.sweep_expired_keys()  # mark any newly-expired keys as revoked before displaying
    keys = persistence.load_license_keys()
    rows = [{"key": k, **v} for k, v in keys.items()]
    rows.sort(key=lambda r: r.get("created", ""), reverse=True)
    return render_template("admin/keys.html", rows=rows)


@app.route("/admin/requests", methods=["GET", "POST"])
@admin_required
def admin_requests():
    if request.method == "POST":
        action = request.form.get("action")
        req_id = request.form.get("req_id", "")
        if action == "approve":
            reqs = persistence.load_requests()
            target = next((r for r in reqs if r["id"] == req_id), None)
            if target:
                new_key = licensing.create_subscription_key(target.get("name", "Pro User"), target.get("email", ""))
                pro_requests.approve_request(req_id, new_key)
        elif action == "reject":
            pro_requests.reject_request(req_id)
        return redirect(url_for("admin_requests"))
    reqs = persistence.load_requests()
    return render_template("admin/requests.html", reqs=reqs)


@app.route("/admin/blog", methods=["GET", "POST"])
@admin_required
def admin_blog():
    posts = persistence.load_blogs()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            new_post = {
                "id": str(int(time.time())),
                "title": request.form.get("title", "").strip(),
                "category": request.form.get("category", "").strip(),
                "excerpt": request.form.get("excerpt", "").strip(),
                "body": request.form.get("body", "").strip(),
                "date": dt.datetime.now().strftime("%Y-%m-%d"),
                "published": request.form.get("published") == "on",
            }
            posts.insert(0, new_post)
            persistence.save_blogs(posts)
        elif action == "update":
            post_id = request.form.get("post_id")
            for p in posts:
                if str(p["id"]) == post_id:
                    p["title"] = request.form.get("title", "").strip()
                    p["category"] = request.form.get("category", "").strip()
                    p["excerpt"] = request.form.get("excerpt", "").strip()
                    p["body"] = request.form.get("body", "").strip()
                    p["published"] = request.form.get("published") == "on"
                    # date intentionally left as the original publish date —
                    # editing content shouldn't bump a post back to the top
                    # of a date-sorted list as if it were brand new.
            persistence.save_blogs(posts)
        elif action == "toggle_publish":
            post_id = request.form.get("post_id")
            for p in posts:
                if str(p["id"]) == post_id:
                    p["published"] = not p.get("published", False)
            persistence.save_blogs(posts)
        elif action == "delete":
            post_id = request.form.get("post_id")
            posts = [p for p in posts if str(p["id"]) != post_id]
            persistence.save_blogs(posts)
        return redirect(url_for("admin_blog"))

    edit_id = request.args.get("edit")
    edit_post = None
    if edit_id:
        edit_post = next((p for p in posts if str(p["id"]) == edit_id), None)
    return render_template("admin/blog.html", posts=posts, edit_post=edit_post)


@app.route("/admin/notifications", methods=["GET", "POST"])
@admin_required
def admin_notifications():
    """Admin-authored notices — discounts or product updates — shown to
    every visitor via the bell dropdown in the nav, and optionally as a
    dismissible top banner. Same create/edit/toggle/delete shape as
    admin_blog above, plus an opt-in 'email me a copy on publish' checkbox
    that reuses the Resend pattern from notifications.py."""
    anns = persistence.load_announcements()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            new_ann = {
                "id": str(int(time.time() * 1000)),  # ms precision — two posts in the same second would otherwise collide
                "type": request.form.get("type", "update"),
                "title": request.form.get("title", "").strip(),
                "message": request.form.get("message", "").strip(),
                "link_url": request.form.get("link_url", "").strip(),
                "link_text": request.form.get("link_text", "").strip() or "Learn more",
                "banner": request.form.get("banner") == "on",
                "active": request.form.get("active") == "on",
                "expires": request.form.get("expires", "").strip(),
                "created": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            anns.insert(0, new_ann)
            persistence.save_announcements(anns)
            if new_ann["active"] and request.form.get("email_me") == "on":
                notifications.notify_admin_announcement_published(
                    new_ann["title"], new_ann["type"], new_ann["message"],
                    site_url=request.url_root)
        elif action == "update":
            ann_id = request.form.get("ann_id")
            for a in anns:
                if str(a["id"]) == ann_id:
                    a["type"] = request.form.get("type", "update")
                    a["title"] = request.form.get("title", "").strip()
                    a["message"] = request.form.get("message", "").strip()
                    a["link_url"] = request.form.get("link_url", "").strip()
                    a["link_text"] = request.form.get("link_text", "").strip() or "Learn more"
                    a["banner"] = request.form.get("banner") == "on"
                    a["active"] = request.form.get("active") == "on"
                    a["expires"] = request.form.get("expires", "").strip()
                    # created intentionally untouched — editing shouldn't
                    # bump it back to the top of the newest-first list.
            persistence.save_announcements(anns)
        elif action == "toggle_active":
            ann_id = request.form.get("ann_id")
            for a in anns:
                if str(a["id"]) == ann_id:
                    a["active"] = not a.get("active", False)
            persistence.save_announcements(anns)
        elif action == "delete":
            ann_id = request.form.get("ann_id")
            anns = [a for a in anns if str(a["id"]) != ann_id]
            persistence.save_announcements(anns)
        return redirect(url_for("admin_notifications"))

    edit_id = request.args.get("edit")
    edit_ann = None
    if edit_id:
        edit_ann = next((a for a in anns if str(a["id"]) == edit_id), None)
    return render_template("admin/notifications.html", anns=anns, edit_ann=edit_ann)


@app.route("/api/announcements")
def api_announcements():
    """Public, unauthenticated — the bell dropdown and top banner fetch
    this on every page load. Deliberately returns only the fields the
    frontend needs, not the raw DB rows."""
    live = persistence.load_active_announcements()
    return jsonify([{
        "id": a["id"],
        "type": a.get("type", "update"),
        "title": a.get("title", ""),
        "message": a.get("message", ""),
        "link_url": a.get("link_url", ""),
        "link_text": a.get("link_text", "Learn more"),
        "banner": bool(a.get("banner")),
        "created": a.get("created", ""),
    } for a in live])


@app.route("/ads.txt")
def ads_txt():
    """AdSense site-verification / IAB ads.txt. Publisher ID comes from an
    env var so it can be changed without a code deploy — set
    ADSENSE_PUBLISHER_ID to the pub-XXXXXXXXXXXXXXXX value AdSense gave you
    (the part after 'ca-' in your ca-pub-... client ID).
    Must be served at the domain root, exactly at /ads.txt — Google checks
    this exact path, not /static/ads.txt.
    """
    pub_id = os.environ.get("ADSENSE_PUBLISHER_ID", "")
    if not pub_id:
        return "", 404
    content = f"google.com, {pub_id}, DIRECT, f08c47fec0942fa0\n"
    return Response(content, mimetype="text/plain")


@app.route("/ads/slot/<slot>")
def ads_slot(slot):
    """Standalone minimal HTML pages for each ad placement, embedded via
    <iframe>. This is the Flask equivalent of Streamlit's components.html()
    iframe isolation — necessary because Adsterra's invoke.js is hardcoded to
    look for one exact container ID (container-5b0c617f15e7e87967b22cafcc23e1b7)
    for every placement. Embedding that same ID directly in the page multiple
    times (banner + sticky footer + interstitial all at once) causes duplicate-ID
    conflicts and the ad script only finds the first one. Iframes give each
    placement its own document, exactly like the original's isolation."""
    if is_pro():
        return "", 204
    templates_map = {
        "banner": "ads/slot_banner.html",
        "sticky_footer": "ads/slot_sticky_footer.html",
        "native_banner": "ads/slot_banner.html",
        "interstitial": "ads/slot_interstitial.html",
    }
    tpl = templates_map.get(slot)
    if not tpl:
        return "", 404
    return render_template(tpl)


@app.route("/webhook/freemius", methods=["POST"])
def freemius_webhook():
    """Freemius server-to-server webhook — this is what actually keeps a
    recurring subscriber's access alive past the first 30 days. Complements
    fs_callback (which only handles the customer's browser landing back
    after the FIRST purchase) — this route handles every renewal after that,
    with no browser involved at all.

    Set up in Freemius: Developer Dashboard → your product → Webhooks →
    Listeners → Add Webhook → URL: https://<your-domain>/webhook/freemius →
    select at minimum: license.extended, license.cancelled, license.expired.
    """
    signature = request.headers.get("X-Signature", "")
    if licensing.FREEMIUS_SECRET_KEY:
        if not signature:
            return jsonify({"error": "Missing signature"}), 401
        import hmac, hashlib
        expected = hmac.new(licensing.FREEMIUS_SECRET_KEY.encode(), request.get_data(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return jsonify({"error": "Invalid signature"}), 401

    data = request.get_json(silent=True) or {}
    event_type = data.get("event", data.get("type", ""))
    license_obj = (data.get("objects") or {}).get("license") or {}
    freemius_license_id = str(license_obj.get("id", ""))
    new_expiration = license_obj.get("expiration", "")

    if event_type not in ("license.extended", "license.cancelled", "license.expired"):
        return jsonify({"success": True, "ignored": event_type}), 200

    result = licensing.sync_license_from_freemius_event(freemius_license_id, event_type, new_expiration)
    return jsonify(result), (200 if result.get("success") else 404)


@app.route("/fs-callback")
def fs_callback():
    """Freemius redirects the customer's browser here after a successful
    checkout (appends ?license_id=X&email=Y as real query params — this is
    NOT a webhook, the customer's own browser lands on this page). Ported
    from the original app's fs_callback page: verify with Freemius, mint (or
    reuse) an internal key, show it with an inline Activate button.

    IMPORTANT — this only works if Freemius is configured to redirect here:
    in your Freemius checkout link settings, set the after-purchase redirect
    URL to https://<your-domain>/fs-callback. Without that, customers land
    on Freemius's own generic thank-you page instead of this one.
    """
    fs_license_id = request.args.get("license_id", "")
    fs_email = request.args.get("email", "")

    if not fs_license_id:
        return render_template("fs_callback.html", error="no_license_id")

    verify_result = licensing.verify_freemius_license(fs_license_id)

    if not verify_result.get("valid"):
        return render_template("fs_callback.html", error="not_verified",
                                license_id=fs_license_id,
                                verify_error=verify_result.get("error", "unknown"))

    # Reuse an existing internal key if this Freemius license was already
    # converted before (e.g. customer refreshed this page)
    keys = persistence.load_license_keys()
    existing_key = next((k for k, v in keys.items() if v.get("freemius_license_id") == fs_license_id), None)

    if existing_key:
        license_key = existing_key
    else:
        limits = persistence.load_limits()
        license_key = licensing.create_subscription_key(
            customer_name=verify_result.get("user_name") or "Pro User",
            customer_email=verify_result.get("user_email") or fs_email,
            subscription_type="monthly",
            freemius_license_id=fs_license_id,
            amount_paid=limits.get("PRO_PRICE_PKR", 0),
        )

    return render_template("fs_callback.html", success=True, license_key=license_key)


@app.route("/fs-callback/activate", methods=["POST"])
def fs_callback_activate():
    """The inline 'Activate Pro Now' button on the fs_callback success page."""
    key = request.form.get("license_key", "").strip()
    result = licensing.activate_vox_license(key, request)
    if result.get("valid"):
        session["license_key"] = key
        return redirect(url_for("studio"))
    return render_template("fs_callback.html", success=True, license_key=key,
                            activate_error=result.get("error", "Activation failed."))


@app.route("/tools")
def tools_hub():
    return render_template("tools.html", lang_options=audio_tools.LANG_OPTIONS, usage=usage_summary(),
                            filedesk_url=os.environ.get("FILEDESK_URL", "").strip())


@app.route("/api/tools/transcribe", methods=["POST"])
def api_transcribe():
    lim = get_limits()
    if not _under_limit("usage_transcribe", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Free daily limit reached ({lim['FREE_DAILY_ACTIONS']}/day). Upgrade to Pro for unlimited."}), 402
    file = request.files.get("file")
    lang_code = request.form.get("lang_code", "en-US")
    if not file:
        return jsonify({"error": "No file uploaded."}), 400
    try:
        result = audio_tools.transcribe(file.read(), file.filename, lang_code)
        _bump_counter("usage_transcribe")
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tools/convert", methods=["POST"])
def api_convert():
    lim = get_limits()
    if not _under_limit("usage_convert", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Free daily limit reached ({lim['FREE_DAILY_ACTIONS']}/day). Upgrade to Pro for unlimited."}), 402
    file = request.files.get("file")
    output_format = request.form.get("output_format", "mp3")
    quality = int(request.form.get("quality", 192))
    if not file:
        return jsonify({"error": "No file uploaded."}), 400
    try:
        out_bytes = audio_tools.convert(file.read(), file.filename, output_format, quality)
        _bump_counter("usage_convert")
        return jsonify({"audio_b64": base64.b64encode(out_bytes).decode("ascii"),
                         "filename": f"converted-{int(time.time())}.{output_format}",
                         "format": output_format})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tools/merge", methods=["POST"])
def api_merge():
    lim = get_limits()
    if not _under_limit("usage_merge", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Free daily limit reached ({lim['FREE_DAILY_ACTIONS']}/day). Upgrade to Pro for unlimited."}), 402
    files = request.files.getlist("files")
    gap_ms = int(request.form.get("gap_ms", 500))
    output_format = request.form.get("output_format", "mp3")
    if len(files) < 2:
        return jsonify({"error": "Add at least 2 files to merge."}), 400
    try:
        pairs = [(f.read(), f.filename) for f in files]
        out_bytes = audio_tools.merge(pairs, gap_ms, output_format)
        _bump_counter("usage_merge")
        return jsonify({"audio_b64": base64.b64encode(out_bytes).decode("ascii"),
                         "filename": f"merged-{int(time.time())}.{output_format}",
                         "format": output_format})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tools/cutter/duration", methods=["POST"])
def api_cutter_duration():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded."}), 400
    try:
        data = file.read()
        duration = audio_tools.get_duration_sec(data, file.filename)
        return jsonify({"duration_sec": duration})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tools/cutter/trim", methods=["POST"])
def api_cutter_trim():
    lim = get_limits()
    if not _under_limit("usage_cutter", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Free daily limit reached ({lim['FREE_DAILY_ACTIONS']}/day). Upgrade to Pro for unlimited."}), 402
    file = request.files.get("file")
    start_sec = float(request.form.get("start_sec", 0))
    end_sec = float(request.form.get("end_sec", 0))
    if not file:
        return jsonify({"error": "No file uploaded."}), 400
    try:
        out_bytes = audio_tools.trim(file.read(), file.filename, start_sec, end_sec)
        _bump_counter("usage_cutter")
        return jsonify({"audio_b64": base64.b64encode(out_bytes).decode("ascii"),
                         "filename": f"trimmed-{int(time.time())}.mp3"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tools/cutter/split", methods=["POST"])
def api_cutter_split():
    lim = get_limits()
    if not _under_limit("usage_cutter", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Free daily limit reached ({lim['FREE_DAILY_ACTIONS']}/day). Upgrade to Pro for unlimited."}), 402
    file = request.files.get("file")
    split_sec = float(request.form.get("split_sec", 0))
    if not file:
        return jsonify({"error": "No file uploaded."}), 400
    try:
        part1, part2 = audio_tools.split(file.read(), file.filename, split_sec)
        _bump_counter("usage_cutter")
        return jsonify({
            "part1_b64": base64.b64encode(part1).decode("ascii"),
            "part2_b64": base64.b64encode(part2).decode("ascii"),
            "filename_base": f"part-{int(time.time())}",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tools/denoise", methods=["POST"])
def api_denoise():
    lim = get_limits()
    if not _under_limit("usage_denoise", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Free daily limit reached ({lim['FREE_DAILY_ACTIONS']}/day). Upgrade to Pro for unlimited."}), 402
    file = request.files.get("file")
    strength = float(request.form.get("strength", 0.5))
    if not file:
        return jsonify({"error": "No file uploaded."}), 400
    try:
        out_bytes = audio_tools.denoise(file.read(), file.filename, strength)
        _bump_counter("usage_denoise")
        return jsonify({"audio_b64": base64.b64encode(out_bytes).decode("ascii"),
                         "filename": f"denoised-{int(time.time())}.mp3"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tools/voicechange", methods=["POST"])
def api_voicechange():
    lim = get_limits()
    if not _under_limit("usage_voicechange", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Free daily limit reached ({lim['FREE_DAILY_ACTIONS']}/day). Upgrade to Pro for unlimited."}), 402
    file = request.files.get("file")
    effect = request.form.get("effect", "pitch_shift")
    if not file:
        return jsonify({"error": "No file uploaded."}), 400
    try:
        params = {}
        if effect == "pitch_shift":
            params["semitones"] = int(request.form.get("semitones", 0))
        elif effect == "robot":
            params["intensity"] = float(request.form.get("intensity", 0.5))
        elif effect == "echo":
            params["delay_ms"] = int(request.form.get("delay_ms", 200))
            params["decay"] = float(request.form.get("decay", 0.5))
        out_bytes = audio_tools.voice_change(file.read(), file.filename, effect, **params)
        _bump_counter("usage_voicechange")
        return jsonify({"audio_b64": base64.b64encode(out_bytes).decode("ascii"),
                         "filename": f"voicechange-{effect}-{int(time.time())}.mp3"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tools/videoxtract", methods=["POST"])
def api_videoxtract():
    lim = get_limits()
    if not _under_limit("usage_videoxtract", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Free daily limit reached ({lim['FREE_DAILY_ACTIONS']}/day). Upgrade to Pro for unlimited."}), 402
    file = request.files.get("file")
    output_format = request.form.get("output_format", "mp3")
    quality = int(request.form.get("quality", 192))
    if not file:
        return jsonify({"error": "No file uploaded."}), 400
    try:
        out_bytes = audio_tools.video_to_audio(file.read(), file.filename, output_format, quality)
        _bump_counter("usage_videoxtract")
        return jsonify({"audio_b64": base64.b64encode(out_bytes).decode("ascii"),
                         "filename": f"extracted-{int(time.time())}.{output_format}",
                         "format": output_format, "size_kb": round(len(out_bytes) / 1024, 1)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tts/preview", methods=["POST"])
def api_preview():
    data = request.get_json(force=True) or {}
    language = data.get("language", "US English")
    voice_id = data.get("voice_id")
    speed_pct = int(data.get("speed_pct", 100))

    if not voice_id:
        return jsonify({"error": "No voice selected."}), 400

    lim = get_limits()
    if not _under_limit("usage_previews", lim["FREE_PREVIEW_LIMIT"]):
        return jsonify({"error": f"Free preview limit reached ({lim['FREE_PREVIEW_LIMIT']}/day). Upgrade to Pro for unlimited previews."}), 402

    text = default_preview_text(language)
    rate_str = f"{speed_pct - 100:+d}%"
    try:
        audio = tts_dispatch(text, voice_id, rate=rate_str, speed_pct=speed_pct)
    except Exception as e:
        return jsonify({"error": f"Preview error: {str(e)}"}), 500

    _bump_counter("usage_previews")
    return send_file(io.BytesIO(audio), mimetype="audio/mpeg", download_name="preview.mp3")


@app.route("/api/tts/generate", methods=["POST"])
def api_generate():
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    voice_id = data.get("voice_id")
    speed_pct = int(data.get("speed_pct", 100))
    ssml_mode = bool(data.get("ssml_mode", False))

    if not text:
        return jsonify({"error": "Please enter some text first."}), 400
    if not voice_id:
        return jsonify({"error": "No voice selected."}), 400

    lim = get_limits()
    char_limit_widget = None if is_pro() else lim["FREE_CHAR_LIMIT"]
    if char_limit_widget and len(text) > char_limit_widget:
        return jsonify({"error": f"Free plan is capped at {char_limit_widget:,} characters per generation. Upgrade to Pro for unlimited length."}), 402

    if _would_exceed_monthly_quota(len(text), lim["FREE_MONTHLY_CHAR_QUOTA"]):
        return jsonify({"error": f"Free plan's monthly quota of {lim['FREE_MONTHLY_CHAR_QUOTA']:,} characters is used up. Upgrade to Pro for unlimited, or wait until next month."}), 402

    if not _under_limit("usage_singles", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Free daily limit reached ({lim['FREE_DAILY_ACTIONS']} generations/day). Upgrade to Pro for unlimited."}), 402

    rate_str = f"{speed_pct - 100:+d}%"
    try:
        audio = tts_dispatch(text, voice_id, rate=rate_str, ssml_mode=ssml_mode, speed_pct=speed_pct)
    except Exception as e:
        return jsonify({"error": f"Error generating audio: {str(e)}"}), 500

    _bump_counter("usage_singles")
    _bump_monthly_chars(len(text))

    timestamp = int(time.time())
    filename = f"tts-{timestamp}.mp3"
    return jsonify({
        "audio_b64": base64.b64encode(audio).decode("ascii"),
        "filename": filename,
        "size_kb": round(len(audio) / 1024, 1),
    })


@app.route("/api/tts/batch", methods=["POST"])
def api_batch():
    data = request.get_json(force=True) or {}
    lines = [ln.strip() for ln in (data.get("lines") or []) if ln.strip()]
    voice_id = data.get("voice_id")
    speed_pct = int(data.get("speed_pct", 100))

    if not lines:
        return jsonify({"error": "No lines to generate."}), 400
    if not voice_id:
        return jsonify({"error": "No voice selected."}), 400

    lim = get_limits()
    max_lines = lim["PRO_BATCH_MAX"] if is_pro() else lim["FREE_BATCH_MAX_LINES"]
    if len(lines) > max_lines:
        return jsonify({"error": f"{'Pro' if is_pro() else 'Free'} plan limit is {max_lines} lines."}), 402

    if not _under_limit("usage_batches", lim["FREE_BATCH_LIMIT"]):
        return jsonify({"error": f"Free batch limit reached ({lim['FREE_BATCH_LIMIT']}/day). Upgrade to Pro for unlimited."}), 402

    total_chars = sum(len(ln) for ln in lines)
    if _would_exceed_monthly_quota(total_chars, lim["FREE_MONTHLY_CHAR_QUOTA"]):
        return jsonify({"error": f"This batch would exceed your monthly quota of {lim['FREE_MONTHLY_CHAR_QUOTA']:,} characters. Upgrade to Pro for unlimited, or wait until next month."}), 402

    rate_str = f"{speed_pct - 100:+d}%"
    results = []
    errors = []
    timestamp_base = int(time.time())

    for idx, line in enumerate(lines):
        try:
            audio = tts_dispatch(line, voice_id, rate=rate_str, speed_pct=speed_pct)
            fname = f"tts-batch-{idx + 1:02d}-{timestamp_base}.mp3"
            results.append({"idx": idx + 1, "text": line, "filename": fname, "audio": audio})
            _bump_monthly_chars(len(line))  # only bump for lines that actually succeeded
        except Exception as e:
            errors.append(f"Line {idx + 1}: {str(e)}")

    if not results:
        return jsonify({"error": "All lines failed to generate.", "details": errors}), 500

    _bump_counter("usage_batches")  # only counts against the daily batch-run quota if something actually succeeded

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in results:
            zf.writestr(item["filename"], item["audio"])
    zip_buf.seek(0)

    return jsonify({
        "clips": [
            {"idx": r["idx"], "text": r["text"], "filename": r["filename"],
             "audio_b64": base64.b64encode(r["audio"]).decode("ascii")}
            for r in results
        ],
        "zip_b64": base64.b64encode(zip_buf.getvalue()).decode("ascii"),
        "zip_filename": f"tts-batch-{timestamp_base}.zip",
        "errors": errors,
    })


@app.route("/api/clone/upload", methods=["POST"])
def api_clone_upload():
    """Pro-only: upload a reference clip (~10s+) to clone a voice from.
    TODO: this saves to /tmp, which is wiped on every Railway redeploy/restart —
    fine for a same-session clone-then-generate flow, but if you want cloned
    voices to persist across sessions, save the reference clip to your
    GitHub-persisted storage (same pattern as your other config data) instead.
    """
    if not is_pro():
        return jsonify({"error": "Voice cloning is a Pro feature."}), 402

    file = request.files.get("reference_audio")
    if not file or not file.filename:
        return jsonify({"error": "No file uploaded."}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".wav", ".mp3", ".m4a", ".ogg"):
        return jsonify({"error": "Please upload a WAV, MP3, M4A, or OGG clip."}), 400

    ref_id = f"{int(time.time())}_{secure_filename(file.filename)}"
    path = os.path.join(CLONE_UPLOAD_DIR, ref_id)
    file.save(path)
    return jsonify({"reference_id": ref_id})


@app.route("/api/clone/generate", methods=["POST"])
def api_clone_generate():
    if not is_pro():
        return jsonify({"error": "Voice cloning is a Pro feature."}), 402

    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    reference_id = data.get("reference_id")

    if not text:
        return jsonify({"error": "Please enter some text first."}), 400
    if len(text) > CLONE_CHAR_LIMIT:
        return jsonify({"error": f"Cloned-voice generations are capped at {CLONE_CHAR_LIMIT} characters (CPU inference is slow — keep clips short)."}), 400
    if not reference_id:
        return jsonify({"error": "Upload a reference clip first."}), 400

    path = os.path.join(CLONE_UPLOAD_DIR, reference_id)
    if not os.path.exists(path):
        return jsonify({"error": "Reference clip not found — please re-upload."}), 400

    job_id = start_clone_job(text, path)
    return jsonify({"job_id": job_id})


@app.route("/api/clone/status/<job_id>")
def api_clone_status(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Unknown job."}), 404

    if job["status"] == "done":
        return jsonify({"status": "done", "audio_b64": base64.b64encode(job["audio"]).decode("ascii")})
    if job["status"] == "error":
        return jsonify({"status": "error", "error": job["error"]})
    return jsonify({"status": job["status"]})


# ---------------------------------------------------------------------------
# Music generation (Replicate-hosted ACE-Step) — Pro-only, real $ cost per run
# ---------------------------------------------------------------------------
MUSIC_MAX_DURATION_SEC = 120  # keep runs (and cost) bounded — tune in admin later if you add a limits field


@app.route("/api/music/generate", methods=["POST"])
def api_music_generate():
    if not is_pro():
        return jsonify({"error": "Music generation is a Pro feature."}), 402

    data = request.get_json(force=True) or {}
    tags = (data.get("tags") or "").strip()
    lyrics = (data.get("lyrics") or "").strip()
    duration = int(data.get("duration", 60))
    instrumental = bool(data.get("instrumental", True))

    if not tags:
        return jsonify({"error": "Describe the style (e.g. 'lofi, chill, piano, 90 bpm')."}), 400
    if duration < 10 or duration > MUSIC_MAX_DURATION_SEC:
        return jsonify({"error": f"Duration must be between 10 and {MUSIC_MAX_DURATION_SEC} seconds."}), 400

    result = music_engine.start_music_job(tags, "" if instrumental else lyrics, duration)
    if result.get("error"):
        return jsonify(result), 503
    return jsonify(result)


@app.route("/api/music/status/<job_id>")
def api_music_status(job_id):
    job = music_engine.get_job(job_id)
    if not job:
        return jsonify({"error": "Unknown job."}), 404
    if job["status"] == "done":
        return jsonify({"status": "done", "audio_b64": base64.b64encode(job["audio"]).decode("ascii")})
    if job["status"] == "error":
        return jsonify({"status": "error", "error": job["error"]})
    return jsonify({"status": job["status"]})


if __name__ == "__main__":
    # HARDENING: debug=True enables the Werkzeug interactive debugger, which
    # allows arbitrary remote code execution if the debug console is ever
    # reachable. Gunicorn (the real entrypoint on the VPS) never runs this
    # __main__ block, but keeping debug=True here is a landmine if this file
    # is ever run directly with `python app.py` on the server as a quick test.
    # Set FLASK_DEBUG=1 explicitly on your own machine if you need it locally.
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
