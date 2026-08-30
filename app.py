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

from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for, flash, Response, g
import os
import re
import io
import time
import threading
import zipfile
import base64
import secrets
import datetime as dt
import markdown as md_lib

from voices import VOICES, FREE_VOICES, default_preview_text
from tts_engine import tts_dispatch, apply_pronunciation_dict
from clone_engine import start_clone_job, get_job
import modal_client
import music_engine
import audio_tools
import persistence
import tool_pages
import licensing
import usage_tracking
import api_keys
import accounts
import pro_requests
import notifications
import promo
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import hmac

CLONE_UPLOAD_DIR = "/tmp/voxcraft_clone_refs"
os.makedirs(CLONE_UPLOAD_DIR, exist_ok=True)
CLONE_CHAR_LIMIT = 6000  # aligned with Modal worker MAX_TOTAL_CHARS for stable commercial quality

# Persistent (survives redeploy/restart, unlike CLONE_UPLOAD_DIR's /tmp) home
# for reference clips a customer has explicitly chosen to save for reuse.
# Only ever populated via /api/clone/voices/save after the consent check —
# never write here directly from the plain upload/generate flow.
VOICE_REFS_DIR = os.environ.get("VOICE_REFS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "voice_refs"))
os.makedirs(VOICE_REFS_DIR, exist_ok=True)
MAX_SAVED_VOICES_PER_LICENSE = 5

# Bump this if the consent wording materially changes, so old consent
# records in persistence.voice_consents stay attributable to the version of
# the text the customer actually agreed to.
VOICE_CONSENT_VERSION = "v1"
VOICE_CONSENT_TEXT = (
    "I confirm I own this voice or have the speaker's explicit permission to "
    "clone it, and I grant VoxCraft a license to store and use this voice "
    "sample to generate speech on my request."
)

# Reference clips uploaded to CLONE_UPLOAD_DIR (via /api/clone/upload) had no
# expiry at all — every clip ever uploaded sat on disk permanently, only
# cleared by a full service restart (PrivateTmp=true in voxcraft.service
# gives the service its own private /tmp, wiped on restart — so this was
# bounded, but only by however long the service happened to stay up between
# restarts, which with Restart=always could be weeks). A clip is only ever
# needed for the few minutes between upload and the matching /api/clone/
# generate call, so anything older than CLONE_REF_MAX_AGE_SECONDS is safe to
# delete — same sweep-thread pattern already used for the clone/music job
# databases in clone_engine.py / music_engine.py.
CLONE_REF_MAX_AGE_SECONDS = 3600  # 1 hour — generous vs. the actual few-minute usage window
_clone_ref_sweep_thread = None


def _start_clone_ref_sweep_thread():
    global _clone_ref_sweep_thread
    if _clone_ref_sweep_thread is not None and _clone_ref_sweep_thread.is_alive():
        return

    def _sweep_loop():
        while True:
            time.sleep(600)  # every 10 minutes — matches the job-DB sweep cadence
            try:
                cutoff = time.time() - CLONE_REF_MAX_AGE_SECONDS
                for fname in os.listdir(CLONE_UPLOAD_DIR):
                    fpath = os.path.join(CLONE_UPLOAD_DIR, fname)
                    try:
                        if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
                            os.remove(fpath)
                    except OSError:
                        pass  # file could've been removed/replaced between listdir and stat — not fatal
            except Exception:
                pass  # never let the sweeper thread itself crash

    _clone_ref_sweep_thread = threading.Thread(target=_sweep_loop, daemon=True)
    _clone_ref_sweep_thread.start()


_start_clone_ref_sweep_thread()

app = Flask(__name__)

# Single source of truth for the canonical domain — used by the canonical
# <link> tag, sitemap.xml, and robots.txt so they always point at the real
# site regardless of which hostname (www, app.voxcraft.site, etc.) a given
# request actually arrived on. Change here only.
CANONICAL_HOST = "https://voxcraft.site"


def static_url(filename: str) -> str:
    """Cache-busted static asset URL: appends ?v=<file mtime> instead of a
    hand-typed version number.

    BUG THIS REPLACES: templates hardcoded ?v=2 on style.css/studio.js/
    clone_music.js (and nothing at all on ads.js/main.js/notifications.js/
    tools.js/music.js). clone_music.js was edited again later (character
    counter, language detection) without bumping v=2 -> v=3, so browsers
    that had already cached v=2 kept serving the stale file forever, since
    from the browser's point of view the URL never changed.

    Fix: derive the version from the file's actual last-modified time on
    disk instead of a manually-maintained number. Any edit to the file
    changes its mtime, which changes the query string, which forces a
    refetch -- there is no longer a number to forget to bump. Falls back to
    v=0 if the file can't be stat'd (e.g. missing) so a typo in the
    filename doesn't crash the page.
    """
    static_path = os.path.join(app.static_folder, filename)
    try:
        version = int(os.path.getmtime(static_path))
    except OSError:
        version = 0
    return url_for("static", filename=filename) + f"?v={version}"


app.jinja_env.globals["static_url"] = static_url

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

# MONITORING: optional Sentry error tracking. Same graceful-degradation
# pattern as RESEND_API_KEY elsewhere — completely inert if SENTRY_DSN
# isn't set, so this is safe to deploy before you've actually signed up
# for Sentry. Once you do, every unhandled exception in the app gets a
# full traceback + request context sent there instead of only ever
# existing in a gunicorn log file nobody's watching in real time.
# traces_sample_rate is kept low (10%) since this is a small single-VPS
# app — full tracing on every request isn't needed to catch errors,
# just adds overhead. send_default_pii=False is deliberate: don't want
# customer emails/IPs flowing into a third-party dashboard by default.
_sentry_dsn = os.environ.get("SENTRY_DSN", "").strip()
if _sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
    sentry_sdk.init(dsn=_sentry_dsn, integrations=[FlaskIntegration()],
                     traces_sample_rate=0.1, send_default_pii=False)

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


# Prefixes deliberately excluded from the visitor counter: static assets
# (not a "visit"), the admin panel itself (so Faisal checking his own
# dashboard doesn't inflate his own traffic numbers), API/webhook calls
# (machine-to-machine, not a page view), and misc crawler/infra paths.
_TRAFFIC_EXCLUDED_PREFIXES = ("/static/", "/admin", "/api/", "/webhook/", "/ads/", "/ads.txt")

# Substrings matched case-insensitively against User-Agent. Covers the bulk
# of non-human traffic: search engine crawlers, SEO/backlink tools, uptime
# monitors, and bare HTTP clients (curl/requests/scanners with no UA
# customization at all). Not exhaustive — a bot that spoofs a normal
# browser UA will still get counted, same as any server-side approach
# without a JS challenge — but this removes the most common, highest-volume
# noise sources that were inflating the daily visitor count.
_BOT_USER_AGENT_MARKERS = (
    "bot", "spider", "crawl", "slurp", "curl/", "python-requests", "go-http-client",
    "wget", "scrapy", "headlesschrome", "phantomjs", "facebookexternalhit",
    "monitor", "pingdom", "uptimerobot", "statuscake", "ahrefsbot", "semrushbot",
    "mj12bot", "dotbot", "petalbot", "bytespider", "yandex", "baiduspider",
)


def _looks_like_bot(request) -> bool:
    ua = request.headers.get("User-Agent", "").lower()
    if not ua:
        return True  # no UA at all is almost never a real browser
    return any(marker in ua for marker in _BOT_USER_AGENT_MARKERS)


@app.before_request
def _track_traffic():
    """One row per (day, ip_hash) — see persistence.log_visit(). GET-only
    so form submissions/API calls from an already-counted page load don't
    double-count; excluded prefixes above; known-bot user agents skipped
    so the admin traffic count reflects real visitors, not crawler/monitor
    noise. Best-effort: a logging failure here should never take down the
    actual page request."""
    if request.method != "GET" or request.path.startswith(_TRAFFIC_EXCLUDED_PREFIXES):
        return
    if _looks_like_bot(request):
        return
    try:
        ip_hash = usage_tracking.hash_ip(usage_tracking.get_client_ip(request))
        persistence.log_visit(ip_hash)
    except Exception:
        pass

# librosa's pitch_shift uses numba, which JIT-compiles on first call —
# ~20s the very first time, milliseconds after. Warming it up here (module
# level, so this runs under gunicorn too, not just `python app.py` directly)
# means the first real Voice Changer user doesn't eat that cost.
#
# BUG FIX: this used to fire in a background thread
# (threading.Thread(target=_warm_up_librosa, daemon=True).start()) so it
# wouldn't block startup. But under --preload, gunicorn's arbiter loads this
# module ONCE in the master process, then fork()s it into both workers —
# and fork() only carries over the state of the thread that CALLS fork(),
# not any other thread that happens to be running at that moment. If the
# arbiter forked while this background thread was still mid-import of
# numpy/librosa, both forked workers inherited numpy in a permanently
# half-initialized state — which surfaced as "partially initialized module
# 'numpy.core.numerictypes' has no attribute 'csingle' (most likely due to
# a circular import)" on every Denoise call in that worker from then on
# (Denoise lazily imports noisereduce, which pulls in numpy — if numpy's
# own state is already broken from the fork race, every subsequent import
# of it fails identically until that worker recycles).
#
# Fixed by calling this SYNCHRONOUSLY instead — it now fully completes in
# the master before gunicorn's arbiter forks, so there's no race window at
# all. Adds ~20s to `systemctl restart voxcraft` (paid once, not per
# worker), which is a fine trade for removing a bug that could silently
# break Denoise for an unpredictable stretch of a worker's lifetime.
def _warm_up_librosa():
    try:
        import numpy as _np
        import librosa as _librosa
        import noisereduce as _nr  # also warm Denoise's dependency, same reasoning
        _librosa.effects.pitch_shift(_np.zeros(2048, dtype=_np.float32), sr=22050, n_steps=1)
        _nr.reduce_noise(y=_np.zeros(4096, dtype=_np.float32), sr=22050)
    except Exception:
        pass  # non-fatal — worst case, the first real request just pays the JIT/import cost instead


_warm_up_librosa()

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


def _license_context() -> dict:
    """Single source of truth for the current session's license status.

    CHANGED: is_pro(), get_plan(), and has_clone_and_music() used to each
    independently call licensing.check_vox_license() — so any request/
    template that touched all three (the nav bar context processor did
    exactly that) hit the license lookup 3 separate times for the same
    session key. Cached on flask.g so it's computed at most once per
    request no matter how many of those get called.

    Also now carries 'name' — the customer name captured at signup (see
    the manual /upgrade payment flow, which collects a real name) or
    "Pro User" as the fallback for auto-generated/Freemius keys that never
    had a name attached — so the nav bar can show who's actually logged in
    instead of just a generic checkmark.
    """
    cached = getattr(g, "license_ctx", None)
    if cached is not None:
        return cached

    key = session.get("license_key")
    if not key:
        ctx = {"valid": False, "plan": "", "name": ""}
    else:
        result = licensing.check_vox_license(key)
        if not result.get("valid"):
            ctx = {"valid": False, "plan": "", "name": ""}
        else:
            ctx = {
                "valid": True,
                "plan": result.get("plan", "pro"),
                "name": result.get("name") or "Pro User",
            }
    g.license_ctx = ctx
    return ctx


def is_pro() -> bool:
    """Real check now: validates the license key stored in this session
    against licensing.check_vox_license() (backed by license_keys.json on
    GitHub). Falls back to False if no key is activated or GITHUB_TOKEN
    isn't configured yet."""
    return _license_context()["valid"]


def get_plan() -> str:
    """'', 'pro', or 'pro_plus' — '' means not Pro at all. Use this (not
    is_pro() alone) anywhere clone/music access is gated, since a valid
    Pro session doesn't automatically mean Pro+."""
    return _license_context()["plan"]


def get_license_name() -> str:
    """Customer name for the active session's license, or '' if not Pro.
    'Pro User' fallback for keys with no name attached (see
    _license_context() docstring)."""
    return _license_context()["name"]


def has_clone_and_music() -> bool:
    return get_plan() == "pro_plus"


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
    # Canonical URL, one rule for the whole site: the current path, absolute,
    # with the query string dropped. This alone resolves the two duplicate-
    # content pairs currently on the site — /blog?tag=X (every tag chip on
    # every post links here) and /upgrade?plan=pro vs ?plan=pro_plus (linked
    # from pricing/landing CTAs) — without needing a per-route override,
    # since both should canonicalize to their bare path anyway. Any future
    # page can override this explicitly by passing canonical_url into its
    # own render_template() call if it ever needs to point elsewhere.
    canonical_url = CANONICAL_HOST + request.path
    return {
        "is_pro_ctx": is_pro(),
        "plan_ctx": get_plan(),
        "license_name_ctx": get_license_name(),
        "has_clone_music_ctx": has_clone_and_music(),
        "account_email_ctx": session.get("account_email", ""),
        "canonical_url": canonical_url,
        "google_site_verification_code": os.environ.get("GOOGLE_SITE_VERIFICATION", ""),
        "adsense_publisher_id": os.environ.get("ADSENSE_PUBLISHER_ID", ""),
        "plausible_domain": os.environ.get("PLAUSIBLE_DOMAIN", ""),
        # Popunder is OFF by default — deliberately paused while AdSense
        # reviews the site (popunders are on Google/Coalition for Better Ads'
        # disallowed list; running one during review risks rejection). Set
        # ENABLE_POPUNDER=1 in Render's env vars to switch it back on after
        # approval — no code change or redeploy needed beyond the env var.
        "enable_popunder_ctx": os.environ.get("ENABLE_POPUNDER", "") == "1",
        # Interstitials are disabled by default while preparing/reviewing the site for AdSense.
        # Re-enable only after approval with ENABLE_INTERSTITIAL=1.
        "enable_interstitial_ctx": os.environ.get("ENABLE_INTERSTITIAL", "") == "1",
        "csrf_token": session.get("csrf_token", ""),
        "voice_count_ctx": sum(len(v) for v in VOICES.values()),
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


@app.route("/healthz")
def healthz():
    """For UptimeRobot (or any external uptime monitor) to ping — checks
    that the DB is actually reachable, not just that the Flask process is
    alive. A process can be running and still serving 500s on every real
    page if the SQLite file got corrupted/locked/deleted; pinging '/'
    wouldn't necessarily catch that the way a real DB round-trip does."""
    try:
        persistence.load_limits()
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 503


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
    recent_posts = [p for p in all_posts if _blog_is_public(p)][:3]
    for _rp in recent_posts:
        _rp["_slug"] = _blog_slug(_rp)

    # Keep marketing numbers in sync with voices.py (single source of truth).
    voice_count = sum(len(v) for v in VOICES.values())
    language_count = len(VOICES)

    return render_template(
        "landing.html",
        featured_voices=featured_voices,
        recent_posts=recent_posts,
        voice_count=voice_count,
        language_count=language_count,
    )


@app.route("/voices")
def voices_page():
    """Nav and external links sometimes hit /voices. Redirect to the
    homepage voice-library section so visitors never see a 404."""
    return redirect(url_for("landing") + "#voices", code=302)


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
    # BUG FIX: this always passed the FREE tier's batch line cap to the
    # template, even for Pro/Pro+ sessions — so the Batch tab displayed
    # "up to 20 lines" (or whatever FREE_BATCH_MAX_LINES is set to) for
    # paying customers too, even though actual enforcement at generation
    # time (line ~1332) already correctly used PRO_BATCH_MAX for them.
    # Cosmetic-only bug, but confusing: the UI looked capped when it wasn't.
    batch_max = lim["PRO_BATCH_MAX"] if is_pro() else lim["FREE_BATCH_MAX_LINES"]
    return render_template("studio.html", voices=active_voices, pro=is_pro(),
                            free_char_limit=lim["FREE_CHAR_LIMIT"], batch_max=batch_max,
                            monthly_char_quota=lim["FREE_MONTHLY_CHAR_QUOTA"],
                            daily_actions=lim["FREE_DAILY_ACTIONS"], batch_limit=lim["FREE_BATCH_LIMIT"],
                            usage=usage_summary(), clone_char_limit=CLONE_CHAR_LIMIT)


@app.route("/voice-cloning")
def voice_cloning():
    """Dedicated, indexable page for AI voice cloning — previously only
    reachable as one tab inside /studio (gated behind Pro+, with almost no
    surrounding written content). Reuses the exact same widget partial as
    the Clone tab on /studio (partials/tool_widgets/voiceclone.html) and
    the same clone_music.js — no duplicated cloning logic, just a second,
    content-rich entry point aimed at people searching for voice cloning
    specifically rather than the Studio as a whole."""
    return render_template("voice_cloning.html", clone_char_limit=CLONE_CHAR_LIMIT)


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
        "No ads", f"Batch up to {limits['PRO_BATCH_MAX']} lines",
    ]
    pro_plus_features = [f.strip() for f in (limits.get("PRO_PLUS_FEATURES") or "").split("|") if f.strip()] or \
        pro_features + ["Voice cloning", "AI music generation"]

    # BUG FIX: "Current plan" was hardcoded onto the Free tier's card
    # regardless of the visitor's actual plan — so a Pro or Pro+ customer
    # would see Free marked as their current plan (confusing/wrong), while
    # their real plan showed the normal "Get Pro"/"Get Pro+" buy button as
    # if they weren't subscribed at all. Now it's driven by the session's
    # actual plan.
    current_plan = get_plan() or "free"
    # Annual display = 10× monthly (2 months free). PKR annual from PRO_PRICE_PKR * 10.
    pro_pkr = int(limits.get("PRO_PRICE_PKR", 840) or 840)
    pro_plus_pkr = int(limits.get("PRO_PLUS_PRICE_PKR", 1680) or 1680)
    plans = [
        {"id": "free", "name": "Free", "price": limits.get("FREE_PRICE_LABEL", "$0"), "period": "forever",
         "pkr": None, "price_annual": None, "pkr_annual": None,
         "limits": free_features,
         "cta": "Current plan" if current_plan == "free" else "Downgrade automatically at renewal",
         "cta_url": None},
        {"id": "pro", "name": "Pro", "price": limits.get("PRO_PRICE_USD_LABEL", "$3"), "period": "/month",
         "price_annual": limits.get("PRO_PRICE_ANNUAL_USD_LABEL", "$30"),
         "pkr": limits.get("PRO_PRICE_LABEL", "840 PKR"),
         "pkr_annual": f"{pro_pkr * 10} PKR",
         "limits": pro_features,
         "cta": "Current plan" if current_plan == "pro" else "Get Pro",
         "cta_url": None if current_plan == "pro" else url_for("upgrade", plan="pro")},
        {"id": "pro_plus", "name": "Pro+", "price": limits.get("PRO_PLUS_PRICE_USD_LABEL", "$6"), "period": "/month",
         "price_annual": limits.get("PRO_PLUS_PRICE_ANNUAL_USD_LABEL", "$60"),
         "pkr": limits.get("PRO_PLUS_PRICE_LABEL", "1680 PKR"),
         "pkr_annual": f"{pro_plus_pkr * 10} PKR",
         "limits": pro_plus_features, "featured": True,
         "cta": "Current plan" if current_plan == "pro_plus" else "Get Pro+",
         "cta_url": None if current_plan == "pro_plus" else url_for("upgrade", plan="pro_plus")},
    ]
    return render_template("pricing.html", plans=plans)


def _developers_ctx(lim):
    """Shared context for /developers and /developers/signup (GET-error and
    POST-success/error re-renders) — was three separate copies of this same
    dict that had already drifted out of sync once (Starter/Pro annual
    price labels only existed in one of the three). One function means
    they can't drift again."""
    return dict(
        api_max_chars=API_MAX_CHARS_PER_REQUEST,
        api_free_quota=lim.get("API_FREE_QUOTA", 10000),
        api_starter_quota=lim.get("API_STARTER_QUOTA", 200000),
        api_starter_price=lim.get("API_STARTER_PRICE_USD_LABEL", "$9"),
        api_starter_price_annual=lim.get("API_STARTER_PRICE_ANNUAL_USD_LABEL", "$90"),
        checkout_url_api_starter=lim.get("CHECKOUT_URL_API_STARTER") or None,
        api_pro_quota=lim.get("API_PRO_QUOTA", 1000000),
        api_pro_price=lim.get("API_PRO_PRICE_USD_LABEL", "$29"),
        api_pro_price_annual=lim.get("API_PRO_PRICE_ANNUAL_USD_LABEL", "$290"),
        checkout_url_api_pro=lim.get("CHECKOUT_URL_API_PRO") or None,
    )


@app.route("/developers")
def developers():
    """Public marketing/landing page for the API product, now fully
    self-serve on both ends: Free signs up instantly on this page (see
    developers_signup below), Starter/Pro send the customer to their own
    Freemius checkout link and the key is auto-issued the moment payment
    succeeds (see fs_callback_api + the freemius webhook) — no admin step
    in either path anymore. /admin/api-keys still exists for manual
    issuance/overrides, it's just no longer required for a customer to get
    a key."""
    lim = persistence.load_limits()
    return render_template("developers.html", **_developers_ctx(lim))


@app.route("/developers/signup", methods=["POST"])
def developers_signup():
    """Free-tier self-serve signup — the only step in the whole API flow
    that still needs no payment at all. Instant key, emailed immediately,
    shown once inline on this page as a fallback if the email doesn't
    land. Deduped by email so re-submitting the form (or a curious repeat
    visitor) doesn't mint a fresh free-quota key every time — the existing
    one just isn't shown again, since the raw key can't be retrieved once
    it's hashed."""
    name = (request.form.get("customer_name") or "").strip()
    email = (request.form.get("customer_email") or "").strip()
    lim = persistence.load_limits()
    quota = int(lim.get("API_FREE_QUOTA", 10000))

    if not name or not email or "@" not in email:
        return render_template("developers.html", **_developers_ctx(lim), signup_error="Enter a name and a valid email.")

    existing = api_keys.find_key_by_email(email, plan="api_free")
    if existing:
        signup_result = {"already_had_key": True, "customer_email": email}
    else:
        result = api_keys.create_api_key(name, email, "api_free", quota)
        notifications.send_api_key_email(email, name, result["raw_key"], "api_free", quota)
        signup_result = {"already_had_key": False, "raw_key": result["raw_key"], "customer_email": email}

    return render_template("developers.html", **_developers_ctx(lim), signup_result=signup_result)


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
    return render_template(
        "activate.html",
        error=result.get("error", "Invalid license key."),
        needs_unlock=result.get("needs_unlock", False),
        attempted_key=key if result.get("needs_unlock") else "",
    )


@app.route("/upgrade", methods=["GET", "POST"])
def upgrade():
    lim = persistence.load_limits()
    # Two separate Freemius checkout links — one per plan. Previously a
    # single CHECKOUT_URL served both, so the "Pay with card" button always
    # sent people to whichever one URL was configured, ignoring which plan
    # they'd actually picked below it. See templates/upgrade.html for how
    # these two now get wired to the plan selector.
    checkout_url = lim.get("CHECKOUT_URL") or None
    checkout_url_pro_plus = lim.get("CHECKOUT_URL_PRO_PLUS") or None
    requested_plan = request.args.get("plan") if request.method == "GET" else request.form.get("plan")
    requested_plan = requested_plan if requested_plan in ("pro", "pro_plus") else "pro"
    requested_billing = request.args.get("billing") if request.method == "GET" else request.form.get("billing")
    requested_billing = requested_billing if requested_billing == "annual" else "monthly"
    # Annual PKR = 10x monthly (2 months free), same math the pricing page
    # uses — kept in sync here so the manual-payment amount shown always
    # matches what pricing.html advertised.
    pro_price_pkr_annual = int(lim.get("PRO_PRICE_PKR", 840) or 840) * 10
    pro_plus_price_pkr_annual = int(lim.get("PRO_PLUS_PRICE_PKR", 1680) or 1680) * 10
    upgrade_ctx = dict(
        checkout_url=checkout_url, checkout_url_pro_plus=checkout_url_pro_plus,
        requested_plan=requested_plan, requested_billing=requested_billing,
        pro_price_usd=lim.get("PRO_PRICE_USD_LABEL", "$3"),
        pro_plus_price_usd=lim.get("PRO_PLUS_PRICE_USD_LABEL", "$6"),
        pro_price_annual_usd=lim.get("PRO_PRICE_ANNUAL_USD_LABEL", "$30"),
        pro_plus_price_annual_usd=lim.get("PRO_PLUS_PRICE_ANNUAL_USD_LABEL", "$60"),
        pro_price_pkr=lim.get("PRO_PRICE_PKR", 840),
        pro_plus_price_pkr=lim.get("PRO_PLUS_PRICE_PKR", 1680),
        pro_price_pkr_annual=pro_price_pkr_annual,
        pro_plus_price_pkr_annual=pro_plus_price_pkr_annual,
    )
    if request.method == "GET":
        # BUG FIX: this previously never read MANUAL_GRACE_HOURS at all on
        # the initial page load — only after submitting the form — so the
        # "access stops working after X hours" text was disconnected from
        # whatever was actually set in /admin/limits.
        grace_hours = lim.get("MANUAL_GRACE_HOURS", 72)
        return render_template("upgrade.html", grace_hours=grace_hours, **upgrade_ctx)
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    payment_method = (request.form.get("payment_method") or "").strip()
    txn_id = (request.form.get("txn_id") or "").strip()

    def _upgrade_error(msg):
        return render_template("upgrade.html", error=msg, **upgrade_ctx)

    if not name or not email:
        return _upgrade_error("Name and email are required.")
    # HARDENING: was only checked client-side (the form's `required`
    # attribute) — trivial to bypass with a direct POST, which is exactly
    # what someone trying to submit garbage/duplicate claims would do.
    if "@" not in email or "." not in email.split("@")[-1]:
        return _upgrade_error("Enter a valid email — your license key gets sent there.")
    if not txn_id or len(txn_id) < 6:
        return _upgrade_error("Enter the transaction/reference ID from your payment confirmation (at least 6 characters).")

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

    # Optional one-time discount promo (manual PKR path). Freemius card
    # checkouts use the matching coupon configured in the Freemius dashboard.
    promo_code = (request.form.get("promo_code") or "").strip()
    promo_info = None
    if promo_code:
        ok, pmsg, prec = promo.validate_for_discount(promo_code, email, request)
        if not ok:
            return _upgrade_error(pmsg)
        # Consume now so a second simultaneous submit from another tab cannot
        # reuse the same code. If submit_pro_request later fails we still
        # keep the redemption (admin can reactivate the code if needed).
        cok, cmsg, _ = promo.consume_discount(
            promo_code, email, request,
            plan=requested_plan,
            amount_before=0,
        )
        if not cok:
            return _upgrade_error(cmsg)
        promo_info = {"code": promo_code, "discount_percent": prec.get("discount_percent", 0)}

    # Expected PKR for OCR amount gate (promo reduces it)
    base_pkr = int(lim.get("PRO_PLUS_PRICE_PKR" if requested_plan == "pro_plus" else "PRO_PRICE_PKR", 0) or 0)
    expected_pkr = base_pkr * 10 if requested_billing == "annual" else base_pkr
    if promo_info and promo_info.get("discount_percent"):
        expected_pkr = int(round(expected_pkr * (100 - int(promo_info["discount_percent"])) / 100))
    elif not promo_info:
        # Still pass full expected amount so OCR amount gate is consistent
        pass

    result = pro_requests.submit_pro_request(
        request, name, email, phone, payment_method, txn_id, screenshot_b64,
        plan=requested_plan, billing=requested_billing,
        expected_amount_override=expected_pkr,
    )
    if result.get("success"):
        # Attach promo metadata onto the request record for admin visibility
        if promo_info and result.get("id"):
            reqs = persistence.load_requests()
            for r in reqs:
                if r.get("id") == result["id"]:
                    r["promo_code"] = promo_info["code"]
                    r["promo_discount_percent"] = promo_info["discount_percent"]
                    break
            persistence.save_requests(reqs)
        if result.get("auto_rejected"):
            return render_template(
                "upgrade.html",
                error=result.get("reject_reason") or "This submission could not be accepted. Please fix and try again.",
                **upgrade_ctx,
            )
        if result.get("auto_approved") and result.get("license_key") and not already_pro:
            session["license_key"] = result["license_key"]  # instant unlock on this device
        return render_template("upgrade.html", submitted=True, req_id=result["id"],
                                auto_approved=result.get("auto_approved", False),
                                grace_hours=result.get("grace_hours"),
                                already_pro=already_pro, **upgrade_ctx)
    return render_template("upgrade.html", error=result.get("error", "Something went wrong. Please try again."),
                            **upgrade_ctx)


# ---------------------------------------------------------------------------
# About / trust pages
# ---------------------------------------------------------------------------
@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/how-we-test")
def how_we_test():
    return render_template("how_we_test.html")


# ---------------------------------------------------------------------------
# Blog publication scheduling
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """URL-safe slug from a title. Keeps it short and stable."""
    import re as _re
    s = (text or "").lower().strip()
    s = _re.sub(r"[^\w\s-]", "", s, flags=_re.UNICODE)
    s = _re.sub(r"[-\s]+", "-", s).strip("-")
    return (s[:90] or "post")


def _blog_slug(post) -> str:
    """Prefer explicit slug field, else derive from title, else fall back to id."""
    explicit = (post.get("slug") or "").strip()
    if explicit:
        return explicit
    title = (post.get("title") or "").strip()
    if title:
        return _slugify(title)
    return str(post.get("id") or "post")


def _blog_is_public(post):
    """A post is public only when published and its optional publish_date has arrived.
    Older posts without publish_date remain fully compatible.
    Dates use the server calendar (YYYY-MM-DD).
    """
    if not post.get("published"):
        return False
    publish_date = (post.get("publish_date") or "").strip()
    if not publish_date:
        return True
    return publish_date <= dt.datetime.now().strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# Blog (public)
# ---------------------------------------------------------------------------
@app.route("/blog")
def blog_list():
    posts = [p for p in persistence.load_blogs() if _blog_is_public(p)]
    posts.sort(key=lambda p: p.get("date", ""), reverse=True)

    # Add lightweight presentation metadata without changing the stored
    # records. Older posts continue to work without a migration.
    for p in posts:
        body_text = re.sub(r"<[^>]+>", " ", md_lib.markdown(p.get("body", "")))
        word_count = len(re.findall(r"\b\w+\b", body_text))
        p["_reading_minutes"] = max(1, round(word_count / 220))
        p["_slug"] = _blog_slug(p)

    categories = []
    for p in posts:
        category = (p.get("category") or "General").strip()
        if category and category not in categories:
            categories.append(category)

    # All tags across every post, for the filter chip list — independent
    # of which tag (if any) is currently selected, so the full set of
    # options stays visible even while filtered down to one.
    all_tags = []
    for p in posts:
        for t in (p.get("tags") or []):
            if t not in all_tags:
                all_tags.append(t)
    all_tags.sort()

    active_tag = (request.args.get("tag") or "").strip().lower()
    if active_tag:
        posts = [p for p in posts if active_tag in (p.get("tags") or [])]

    return render_template("blog_list.html", posts=posts, categories=categories,
                            all_tags=all_tags, active_tag=active_tag)


# A small, explicit mapping keeps article-to-product links predictable.
# Each value is (endpoint, kwargs, label) — kwargs is passed to url_for()
# so entries can point at either a plain page (voice cloning, studio) or a
# specific /tools/<slug> page (tool_page endpoint takes a slug kwarg).
#
# BUG FIX: every non-TTS entry here used to point at the generic /tools
# hub ("tools_hub") rather than the specific dedicated page for that tool
# — e.g. a post about denoising linked to the whole tools directory
# instead of straight to /tools/remove-background-noise. That was fine
# back when /tools embedded every tool's widget on one page, but since the
# hub became a lightweight directory (tools_hub is no longer where the
# actual tool lives), these stale links meant a reader had to click
# through an extra page to reach the tool the article was actually about.
BLOG_TOOL_LINKS = {
    "tts": ("studio", {}, "Open Voice Studio"),
    "text-to-speech": ("studio", {}, "Open Voice Studio"),
    "voice": ("studio", {}, "Explore Voices"),
    "urdu-tts": ("studio", {}, "Try Urdu TTS"),
    "hindi-tts": ("studio", {}, "Try Hindi TTS"),
    "arabic-tts": ("studio", {}, "Try Arabic TTS"),
    "voice cloning": ("voice_cloning", {}, "Try Voice Cloning"),
    "voice-cloning": ("voice_cloning", {}, "Try Voice Cloning"),
    "transcription": ("tool_page", {"slug": "transcribe-audio-to-text"}, "Open Transcribe"),
    "audio transcription": ("tool_page", {"slug": "transcribe-audio-to-text"}, "Open Transcribe"),
    "convert": ("tool_page", {"slug": "convert-audio-format"}, "Open Convert"),
    "audio converter": ("tool_page", {"slug": "convert-audio-format"}, "Open Convert"),
    "merge": ("tool_page", {"slug": "merge-audio-files"}, "Open Merge"),
    "audio merger": ("tool_page", {"slug": "merge-audio-files"}, "Open Merge"),
    "cutter": ("tool_page", {"slug": "trim-cut-audio"}, "Open Cutter"),
    "audio cutter": ("tool_page", {"slug": "trim-cut-audio"}, "Open Cutter"),
    "denoise": ("tool_page", {"slug": "remove-background-noise"}, "Open Denoise"),
    "noise removal": ("tool_page", {"slug": "remove-background-noise"}, "Open Denoise"),
    "voice changer": ("tool_page", {"slug": "voice-changer"}, "Open Voice Changer"),
    "video to audio": ("tool_page", {"slug": "extract-audio-from-video"}, "Open Video-to-Audio"),
    "video extract": ("tool_page", {"slug": "extract-audio-from-video"}, "Open Video-to-Audio"),
    "music": ("tool_page", {"slug": "ai-music-generator"}, "Open Music Generator"),
    "api": ("developers", {}, "Explore the Developer API"),
    "developer-api": ("developers", {}, "Explore the Developer API"),
}


def _blog_tool_link(post):
    """Return a safe product link for a post's optional related_tool field."""
    key = (post.get("related_tool") or "").strip().lower()
    entry = BLOG_TOOL_LINKS.get(key)
    if not entry:
        return None
    endpoint, kwargs, label = entry
    return {"url": url_for(endpoint, **kwargs), "label": label}


@app.route("/blog/<path:identifier>")
def blog_detail(identifier):
    posts = persistence.load_blogs()
    # Match by slug first (preferred SEO URL), then by numeric/string id
    post = next(
        (p for p in posts if _blog_is_public(p) and _blog_slug(p) == identifier),
        None,
    )
    if post is None:
        post = next(
            (p for p in posts if _blog_is_public(p) and str(p.get("id")) == str(identifier)),
            None,
        )
        # Old numeric URL → permanent redirect to readable slug
        if post is not None:
            canonical_slug = _blog_slug(post)
            if canonical_slug != identifier:
                return redirect(url_for("blog_detail", identifier=canonical_slug), code=301)
    if not post:
        return render_template("blog_list.html", posts=[], not_found=True), 404

    post_html = md_lib.markdown(post.get("body", ""), extensions=["tables", "fenced_code"])
    body_text = re.sub(r"<[^>]+>", " ", post_html)
    word_count = len(re.findall(r"\b\w+\b", body_text))
    reading_minutes = max(1, round(word_count / 220))

    # Prefer explicitly related posts, then fall back to recent posts in the
    # same category. Never expose drafts.
    category = (post.get("category") or "").strip().lower()
    related_posts = [
        p for p in posts
        if str(p.get("id")) != str(post.get("id"))
        and _blog_is_public(p)
        and category
        and (p.get("category") or "").strip().lower() == category
    ][:3]
    if len(related_posts) < 3:
        for candidate in posts:
            if str(candidate.get("id")) == str(post.get("id")) or candidate in related_posts:
                continue
            if _blog_is_public(candidate):
                related_posts.append(candidate)
            if len(related_posts) >= 3:
                break

    for rp in related_posts:
        rp["_slug"] = _blog_slug(rp)

    return render_template(
        "blog_detail.html",
        post=post,
        post_html=post_html,
        reading_minutes=reading_minutes,
        author=post.get("author") or "VoxCraft Team",
        updated_date=post.get("updated_date") or post.get("date", ""),
        related_tool=_blog_tool_link(post),
        related_posts=related_posts,
    )


# ---------------------------------------------------------------------------
# Static content pages
# ---------------------------------------------------------------------------
@app.route("/sitemap.xml")
def sitemap():
    """Dynamically generated — includes every public page plus every
    published blog post, using whatever domain the request actually came in
    on (so it's correct whether you're on Render's default domain or your
    real one, without needing a hardcoded base URL)."""
    base = CANONICAL_HOST
    static_paths = [
        ("/", "1.0", "weekly"),
        ("/studio", "0.9", "weekly"),
        ("/voice-cloning", "0.85", "monthly"),
        ("/tools", "0.9", "weekly"),
        *[(f"/tools/{slug}", "0.75", "monthly") for slug in tool_pages.TOOL_PAGES],
        ("/pricing", "0.8", "monthly"),
        ("/developers", "0.7", "monthly"),
        ("/blog", "0.7", "weekly"),
        # /activate and /upgrade intentionally omitted — utility pages, noindex
        ("/privacy", "0.3", "yearly"),
        ("/terms", "0.3", "yearly"),
        ("/about", "0.4", "yearly"),
        ("/how-we-test", "0.4", "yearly"),
        ("/contact", "0.4", "yearly"),
    ]
    urls = [{"loc": f"{base}{path}", "priority": priority, "changefreq": freq}
            for path, priority, freq in static_paths]

    for post in persistence.load_blogs():
        if _blog_is_public(post):
            urls.append({
                "loc": f"{base}/blog/{_blog_slug(post)}",
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
    base = CANONICAL_HOST
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


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "GET":
        # Lets other pages deep-link into a pre-selected topic — e.g. the
        # /developers page's "Request API access" button sends people here
        # with ?topic=API%20Access already chosen, instead of making them
        # find it in the dropdown themselves.
        topic = request.args.get("topic", "").strip()
        return render_template("contact.html", topic=topic if topic else None)

    # Honeypot: a hidden field real visitors never fill in. Bots that
    # blindly fill every input trip this and get silently dropped —
    # no CSRF-style rejection needed, just show the same success state.
    if (request.form.get("website") or "").strip():
        return render_template("contact.html", submitted=True)

    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip()
    topic = (request.form.get("topic") or "General").strip()
    message = (request.form.get("message") or "").strip()

    errors = {}
    if not name:
        errors["name"] = "Enter your name."
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        errors["email"] = "Enter a valid email so we can reply."
    if not message or len(message) < 10:
        errors["message"] = "Message is too short — give us a bit more detail."

    if errors:
        return render_template("contact.html", errors=errors, name=name, email=email,
                                topic=topic, message=message)

    # Route common support topics to self-serve pages — no admin email.
    topic_l = topic.lower()
    if any(k in topic_l for k in ("missing key", "resend key", "lost key", "where is my key")):
        return redirect(url_for("resend_key"))
    if any(k in topic_l for k in ("device", "unlock", "another device", "new phone", "new device")):
        return redirect(url_for("unlock_device"))
    if any(k in topic_l for k in ("payment status", "request status", "pending payment", "not approved")):
        return redirect(url_for("request_status"))
    if any(k in topic_l for k in ("promo", "redeem code", "free trial")):
        return redirect(url_for("redeem_promo"))

    req_id = secrets.token_hex(4)
    sent = notifications.notify_contact_message(name, email, topic, message, req_id=req_id,
                                                  site_url=request.host_url)
    # Even if email delivery fails (e.g. RESEND_API_KEY not set yet), don't
    # show the visitor an error — the message isn't lost from their side,
    # and a "something went wrong" screen after a real submission just
    # invites duplicate sends. Log server-side instead.
    if not sent:
        app.logger.warning(f"Contact form message not delivered (req {req_id}) — check RESEND_API_KEY/ADMIN_EMAIL.")

    return render_template("contact.html", submitted=True, req_id=req_id)


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
    today_visitors = persistence.get_daily_traffic(1)[0]["visitors"]
    return render_template("admin/dashboard.html",
                            total_keys=len(keys), active_keys=active_keys,
                            pending_reqs=pending_reqs, total_posts=len(posts),
                            total_anns=len(anns), live_anns=live_anns,
                            today_visitors=today_visitors,
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
            # Default matches len of FREE_VOICES in voices.py (currently 27).
            "FREE_VOICES_COUNT": int(request.form.get("FREE_VOICES_COUNT", 27)),
            "PRO_PRICE_PKR": int(request.form.get("PRO_PRICE_PKR", 840)),
            "PRO_PRICE_LABEL": request.form.get("PRO_PRICE_LABEL", "840 PKR"),
            "PRO_PRICE_USD_LABEL": request.form.get("PRO_PRICE_USD_LABEL", "$3"),
            "PRO_PRICE_ANNUAL_USD_LABEL": request.form.get("PRO_PRICE_ANNUAL_USD_LABEL", "$30"),
            "PRO_PLUS_PRICE_PKR": int(request.form.get("PRO_PLUS_PRICE_PKR", 1680)),
            "PRO_PLUS_PRICE_LABEL": request.form.get("PRO_PLUS_PRICE_LABEL", "1680 PKR"),
            "PRO_PLUS_PRICE_USD_LABEL": request.form.get("PRO_PLUS_PRICE_USD_LABEL", "$6"),
            "PRO_PLUS_PRICE_ANNUAL_USD_LABEL": request.form.get("PRO_PLUS_PRICE_ANNUAL_USD_LABEL", "$60"),
            "FREE_PRICE_LABEL": request.form.get("FREE_PRICE_LABEL", "$0"),
            "CHECKOUT_URL": request.form.get("CHECKOUT_URL", ""),
            "CHECKOUT_URL_PRO_PLUS": request.form.get("CHECKOUT_URL_PRO_PLUS", ""),
            "FREE_FEATURES": request.form.get("FREE_FEATURES", ""),
            "PRO_FEATURES": request.form.get("PRO_FEATURES", ""),
            "AUTO_APPROVE_MANUAL": request.form.get("AUTO_APPROVE_MANUAL") == "on",
            "MANUAL_GRACE_HOURS": int(request.form.get("MANUAL_GRACE_HOURS", 72)),
            "API_FREE_QUOTA": int(request.form.get("API_FREE_QUOTA", 10000)),
            "API_STARTER_QUOTA": int(request.form.get("API_STARTER_QUOTA", 200000)),
            "API_STARTER_PRICE_USD_LABEL": request.form.get("API_STARTER_PRICE_USD_LABEL", "$9"),
            "API_STARTER_PRICE_ANNUAL_USD_LABEL": request.form.get("API_STARTER_PRICE_ANNUAL_USD_LABEL", "$90"),
            "CHECKOUT_URL_API_STARTER": request.form.get("CHECKOUT_URL_API_STARTER", ""),
            "API_PRO_QUOTA": int(request.form.get("API_PRO_QUOTA", 1000000)),
            "API_PRO_PRICE_USD_LABEL": request.form.get("API_PRO_PRICE_USD_LABEL", "$29"),
            "API_PRO_PRICE_ANNUAL_USD_LABEL": request.form.get("API_PRO_PRICE_ANNUAL_USD_LABEL", "$290"),
            "CHECKOUT_URL_API_PRO": request.form.get("CHECKOUT_URL_API_PRO", ""),
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
            licensing.create_new_key_manual(plan=request.form.get("plan", "pro"),
                                             subscription_type=request.form.get("duration", "monthly"))
        elif action == "revoke":
            licensing.revoke_key(key)
        elif action == "unrevoke":
            licensing.unrevoke_key(key)
        elif action == "delete":
            licensing.delete_key(key)
        elif action == "reset_device":
            licensing.reset_device_lock(key)
        elif action == "toggle_plan":
            licensing.set_plan(key)
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
                plan = target.get("plan_requested", "pro")
                # Grant the duration the customer actually paid for — an
                # annual manual-payment request approved here previously got
                # the same hardcoded 30-day key as a monthly one, since
                # billing period was never captured or passed through.
                billing = target.get("billing_requested", "monthly")
                new_key = licensing.create_subscription_key(target.get("name", "Pro User"), target.get("email", ""),
                                                              plan=plan,
                                                              subscription_type="annual" if billing == "annual" else "monthly")
                pro_requests.approve_request(req_id, new_key)
                _provision_paid_account(target.get("email", ""), target.get("name", "Pro User"),
                                         "VoxCraft Pro+" if plan == "pro_plus" else "VoxCraft Pro")
        elif action == "reject":
            pro_requests.reject_request(req_id)
        return redirect(url_for("admin_requests"))
    reqs = persistence.load_requests()
    lim = persistence.load_limits()
    return render_template("admin/requests.html", reqs=reqs,
                            pro_price_pkr=lim.get("PRO_PRICE_PKR", 840),
                            pro_plus_price_pkr=lim.get("PRO_PLUS_PRICE_PKR", 1680))


@app.route("/admin/traffic")
@admin_required
def admin_traffic():
    days = int(request.args.get("days", 30))
    days = max(7, min(days, 90))  # sane bounds — a bad ?days= value shouldn't trigger a huge query
    daily = persistence.get_daily_traffic(days)
    chart_data = list(reversed(daily))  # oldest-first for left-to-right chart reading
    today_stats = daily[0] if daily else {"visitors": 0, "pageviews": 0}
    month_visitors = sum(d["visitors"] for d in daily[:30])
    month_pageviews = sum(d["pageviews"] for d in daily[:30])
    max_visitors = max((d["visitors"] for d in chart_data), default=0) or 1
    return render_template("admin/traffic.html", daily=daily, chart_data=chart_data,
                            today_stats=today_stats, month_visitors=month_visitors,
                            month_pageviews=month_pageviews, max_visitors=max_visitors,
                            days=days)


@app.route("/admin/blog", methods=["GET", "POST"])
@admin_required
def admin_blog():
    def parse_tags(raw: str) -> list:
        """'urdu, tts,  tutorial' -> ['urdu', 'tts', 'tutorial'] — trims
        whitespace, drops empties from stray commas, lowercases for
        consistent matching/display, and de-dupes while preserving order."""
        seen = set()
        out = []
        for t in (raw or "").split(","):
            t = t.strip().lower()
            if t and t not in seen:
                seen.add(t)
                out.append(t)
        return out

    posts = persistence.load_blogs()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            today = dt.datetime.now().strftime("%Y-%m-%d")
            new_post = {
                "id": str(int(time.time() * 1000)),
                "title": request.form.get("title", "").strip(),
                "category": request.form.get("category", "").strip(),
                "tags": parse_tags(request.form.get("tags", "")),
                "excerpt": request.form.get("excerpt", "").strip(),
                "body": request.form.get("body", "").strip(),
                "author": request.form.get("author", "").strip() or "VoxCraft Team",
                "updated_date": request.form.get("updated_date", "").strip() or today,
                "related_tool": request.form.get("related_tool", "").strip().lower(),
                "date": today,
                "publish_date": request.form.get("publish_date", "").strip(),
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
                    p["tags"] = parse_tags(request.form.get("tags", ""))
                    p["excerpt"] = request.form.get("excerpt", "").strip()
                    p["body"] = request.form.get("body", "").strip()
                    p["author"] = request.form.get("author", "").strip() or p.get("author") or "VoxCraft Team"
                    p["updated_date"] = request.form.get("updated_date", "").strip() or dt.datetime.now().strftime("%Y-%m-%d")
                    p["related_tool"] = request.form.get("related_tool", "").strip().lower()
                    p["publish_date"] = request.form.get("publish_date", p.get("publish_date", "")).strip()
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


@app.route("/admin/pronunciation", methods=["GET", "POST"])
@admin_required
def admin_pronunciation():
    """Global pronunciation dictionary — plain find/say word substitution
    applied to Studio TTS text right before it's sent to edge-tts. Same
    create/edit/delete shape as admin_blog/admin_notifications above.

    Deliberately global rather than per-language/per-voice: one word (a
    brand name, an acronym) is usually mispronounced the same way
    regardless of which voice reads it, so a single shared list avoids
    the same entry needing to be duplicated across every language."""
    entries = persistence.load_pronunciation_dict()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            new_entry = {
                "id": str(int(time.time() * 1000)),
                "find": request.form.get("find", "").strip(),
                "say": request.form.get("say", "").strip(),
                "match_case": request.form.get("match_case") == "on",
                "note": request.form.get("note", "").strip(),
            }
            if new_entry["find"] and new_entry["say"]:
                entries.insert(0, new_entry)
                persistence.save_pronunciation_dict(entries)
        elif action == "update":
            entry_id = request.form.get("entry_id")
            for e in entries:
                if str(e["id"]) == entry_id:
                    e["find"] = request.form.get("find", "").strip()
                    e["say"] = request.form.get("say", "").strip()
                    e["match_case"] = request.form.get("match_case") == "on"
                    e["note"] = request.form.get("note", "").strip()
            persistence.save_pronunciation_dict(entries)
        elif action == "delete":
            entry_id = request.form.get("entry_id")
            entries = [e for e in entries if str(e["id"]) != entry_id]
            persistence.save_pronunciation_dict(entries)
        return redirect(url_for("admin_pronunciation"))

    edit_id = request.args.get("edit")
    edit_entry = None
    if edit_id:
        edit_entry = next((e for e in entries if str(e["id"]) == edit_id), None)
    return render_template("admin/pronunciation.html", entries=entries, edit_entry=edit_entry)


@app.route("/admin/api-keys", methods=["GET", "POST"])
@admin_required
def admin_api_keys():
    """Issue/revoke developer API keys (see api_keys.py for the full
    design). Deliberately admin-issued rather than self-serve for now —
    the customer pays through the existing manual/Freemius flow, then the
    admin creates the key here, which both persists it (hashed) and emails
    the raw key to the customer in one action. A self-serve signup+billing
    flow can replace the manual creation step later without touching
    api_keys.py's core mechanics."""
    keys = persistence.load_api_keys()
    just_created = None

    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            name = request.form.get("customer_name", "").strip()
            email = request.form.get("customer_email", "").strip()
            plan = request.form.get("plan", "").strip() or "api_starter"
            try:
                quota = int(request.form.get("monthly_char_quota", "200000"))
            except ValueError:
                quota = 200000
            if name and email and quota > 0:
                result = api_keys.create_api_key(name, email, plan, quota)
                just_created = result  # {"raw_key": ..., "record": ...} — shown ONCE on this response only
                sent = notifications.send_api_key_email(email, name, result["raw_key"], plan, quota)
                if not sent:
                    app.logger.warning(f"API key created for {email} but email delivery failed — raw key must be copied from this page now, it cannot be retrieved again.")
                keys = persistence.load_api_keys()
        elif action == "revoke":
            api_keys.revoke_key(request.form.get("key_id"))
            keys = persistence.load_api_keys()
        elif action == "unrevoke":
            api_keys.unrevoke_key(request.form.get("key_id"))
            keys = persistence.load_api_keys()
        elif action == "delete":
            api_keys.delete_key(request.form.get("key_id"))
            keys = persistence.load_api_keys()

    # Attach live usage to each key for display — read-only peek, no lock
    # needed here (see peek_api_key_usage's docstring).
    for k in keys:
        k["usage"] = api_keys.get_usage(k["key_hash"])

    return render_template("admin/api_keys.html", keys=keys, just_created=just_created)


@app.route("/admin/promos", methods=["GET", "POST"])
@admin_required
def admin_promos():
    """Create / enable / disable / delete promo codes and view redemptions."""
    error = success = None
    if request.method == "POST":
        action = request.form.get("action")
        code = request.form.get("code", "")
        if action == "create":
            # Multi-select plans (checkboxes name="plans"); fall back to single "plan"
            selected_plans = request.form.getlist("plans") or [request.form.get("plan", "pro")]
            ok, msg, rec = promo.create_promo(
                code=request.form.get("code", ""),
                promo_type=request.form.get("promo_type", "free"),
                plan=selected_plans,
                duration_months=request.form.get("duration_months", 1),
                discount_percent=request.form.get("discount_percent", 0),
                expires_at=request.form.get("expires_at", ""),
                max_uses=request.form.get("max_uses", 0),
                note=request.form.get("note", ""),
            )
            if ok:
                success = msg
                persistence.append_audit("promo_create", f"{rec.get('code')} type={rec.get('type')}")
            else:
                error = msg
        elif action == "deactivate":
            ok, msg = promo.deactivate_promo(code)
            success = msg if ok else None
            error = None if ok else msg
            if ok:
                persistence.append_audit("promo_deactivate", code)
        elif action == "activate":
            ok, msg = promo.activate_promo(code)
            success = msg if ok else None
            error = None if ok else msg
            if ok:
                persistence.append_audit("promo_activate", code)
        elif action == "delete":
            ok, msg = promo.delete_promo(code)
            success = msg if ok else None
            error = None if ok else msg
            if ok:
                persistence.append_audit("promo_delete", code)
    promos = promo.list_promos()
    redemptions = persistence.load_promo_redemptions()
    redemptions.sort(key=lambda r: r.get("redeemed_at", ""), reverse=True)
    today = dt.datetime.now().strftime("%Y-%m-%d")
    soon = (dt.datetime.now() + dt.timedelta(days=7)).strftime("%Y-%m-%d")
    return render_template(
        "admin/promos.html",
        promos=promos,
        redemptions=redemptions,
        today=today,
        soon=soon,
        error=error,
        success=success,
    )


@app.route("/redeem", methods=["GET", "POST"])
def redeem_promo():
    """Public page: redeem a free-plan promo code (one-time per email + device)."""
    if request.method == "GET":
        return render_template("redeem.html", code=request.args.get("code", ""))

    limited = promo.check_redeem_rate_limit(request)
    if limited:
        return render_template("redeem.html", error=limited,
                               code=request.form.get("code", ""),
                               name=request.form.get("name", ""),
                               email=request.form.get("email", ""))

    code = request.form.get("code", "")
    name = request.form.get("name", "")
    email = request.form.get("email", "")
    site_url = request.url_root.rstrip("/")
    ok, msg, result = promo.redeem_free(code, email, name, request, site_url=site_url)
    if ok:
        persistence.append_audit("promo_redeem_free", f"{code} → {email}", actor=email)
        return render_template("redeem.html", success=msg, result=result)
    return render_template(
        "redeem.html",
        error=msg,
        code=code,
        name=name,
        email=email,
    )


@app.route("/api/promo/validate", methods=["POST"])
def api_promo_validate():
    """Live discount validation for the upgrade page (AJAX). Does NOT consume the code."""
    data = request.get_json(silent=True) or {}
    code = data.get("code") or request.form.get("code", "")
    email = data.get("email") or request.form.get("email", "")
    ok, msg, rec = promo.validate_for_discount(code, email, request)
    if not ok:
        return jsonify({"ok": False, "message": msg})
    return jsonify({
        "ok": True,
        "message": msg,
        "discount_percent": rec.get("discount_percent", 0),
    })


@app.route("/resend-key", methods=["GET", "POST"])
def resend_key():
    """Self-serve: customer enters email + last 4 of txn ID (or full key prefix)
    to have their license / API key re-emailed."""
    if request.method == "GET":
        return render_template("resend_key.html")

    email = (request.form.get("email") or "").strip().lower()
    hint = (request.form.get("hint") or "").strip()
    if not email or "@" not in email:
        return render_template("resend_key.html", error="Enter a valid email.")
    if len(hint) < 4:
        return render_template("resend_key.html", error="Enter at least the last 4 characters of your transaction ID or license key.", email=email)

    # Look up license keys by email
    keys = persistence.load_license_keys()
    matched_keys = []
    for k, info in keys.items():
        if (info.get("customer_email") or "").strip().lower() != email:
            continue
        if not licensing.is_subscription_active(info) or info.get("revoked"):
            continue
        # Soft match: hint appears in key or in any stored txn-like field
        blob = (k + " " + str(info.get("freemius_license_id", ""))).upper()
        if hint.upper() in blob or blob.endswith(hint.upper()):
            matched_keys.append(k)

    # Also check pro requests for txn_id match
    if not matched_keys:
        for r in persistence.load_requests():
            if (r.get("email") or "").strip().lower() != email:
                continue
            txn = (r.get("txn_id") or "")
            if hint.lower() in txn.lower() or txn.lower().endswith(hint.lower()):
                # Find key created for this request if any
                for k, info in keys.items():
                    if (info.get("customer_email") or "").strip().lower() == email and licensing.is_subscription_active(info):
                        matched_keys.append(k)
                        break

    sent_any = False
    if matched_keys:
        name = "Customer"
        for k, info in keys.items():
            if k in matched_keys:
                name = info.get("customer_name") or name
                break
        for k in matched_keys[:3]:
            if notifications.send_key_email(email, name, k):
                sent_any = True
        persistence.append_audit("resend_key", f"{email} keys={len(matched_keys)}", actor=email)

    # API keys
    api_matched = False
    for ak in persistence.load_api_keys():
        if (ak.get("customer_email") or "").strip().lower() == email and ak.get("active"):
            # We cannot re-show the raw key (hashed at rest). Tell them to contact support
            # or we email a note that they already have an active key.
            api_matched = True
            break

    if sent_any:
        return render_template("resend_key.html", success="If a matching active license was found, the key has been re-sent to your email.")
    if api_matched and not matched_keys:
        return render_template("resend_key.html", success="You have an active API key on this email. For security the full key cannot be re-displayed; contact support if you lost it.")
    # Always show generic success to avoid email enumeration
    return render_template("resend_key.html", success="If a matching active license was found, the key has been re-sent to your email.")


@app.route("/request-status", methods=["GET", "POST"])
def request_status():
    """Self-serve: customer checks payment / pro-request status without emailing admin."""
    if request.method == "GET":
        return render_template("request_status.html")

    email = (request.form.get("email") or "").strip().lower()
    hint = (request.form.get("hint") or "").strip()
    if not email or "@" not in email:
        return render_template("request_status.html", error="Enter the email you used when paying.")
    if len(hint) < 4:
        return render_template(
            "request_status.html",
            error="Enter your request ID (REQ-…) or at least 4 characters of the transaction ID.",
            email=email,
        )

    matches = []
    for r in persistence.load_requests():
        if (r.get("email") or "").strip().lower() != email:
            continue
        rid = (r.get("id") or "")
        txn = (r.get("txn_id") or "")
        if hint.upper() in rid.upper() or hint.lower() in txn.lower() or txn.lower().endswith(hint.lower()):
            matches.append(r)

    if not matches:
        # Generic — avoid confirming whether email exists
        return render_template(
            "request_status.html",
            not_found=True,
            email=email,
        )

    # Newest first
    matches.sort(key=lambda x: x.get("date", ""), reverse=True)
    results = []
    for r in matches[:5]:
        status = r.get("status", "pending")
        if status == "approved":
            msg = "Approved — your license key was emailed. Activate it on the Activate page."
        elif status == "rejected":
            msg = r.get("reject_reason") or "Rejected. Fix the issue and submit a new payment request."
        elif status in ("pending", "payment_pending"):
            msg = "Under review. You’ll get an email when it’s approved (usually within a day)."
        else:
            msg = f"Status: {status}"
        results.append({
            "id": r.get("id"),
            "date": r.get("date"),
            "status": status,
            "plan": r.get("plan_requested", "pro"),
            "message": msg,
            "auto_approved": r.get("auto_approved"),
        })
    return render_template("request_status.html", results=results, email=email)


@app.route("/unlock-device", methods=["GET", "POST"])
def unlock_device():
    """Self-serve device unlock: prove you own the key (key + matching email)
    → we email a one-time link → clicking it clears the device lock so the
    key can be activated on the new device."""
    if request.method == "GET":
        return render_template(
            "unlock_device.html",
            prefill_key=request.args.get("key", ""),
        )

    key = (request.form.get("license_key") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    if not key or not email or "@" not in email:
        return render_template(
            "unlock_device.html",
            error="Enter your license key and the email on the license.",
            prefill_key=key,
            email=email,
        )

    # Resolve internal key (supports Freemius keys that wrap an internal one)
    keys = persistence.load_license_keys()
    info = keys.get(key)
    if not info:
        # Maybe they typed a Freemius id — find by freemius_license_id or email
        for k, v in keys.items():
            if (v.get("freemius_license_id") or "") == key:
                key, info = k, v
                break
            if (v.get("customer_email") or "").strip().lower() == email and licensing.is_subscription_active(v):
                # Don't auto-pick by email alone when key doesn't match — too loose
                pass

    # Generic response either way (no enumeration)
    generic_ok = (
        "If the key and email match an active license, we sent an unlock link. "
        "Check your inbox (and spam). The link works once and expires in 1 hour."
    )

    if not info or not licensing.is_subscription_active(info) or info.get("revoked"):
        return render_template("unlock_device.html", success=generic_ok)

    stored_email = (info.get("customer_email") or "").strip().lower()
    if stored_email != email:
        return render_template("unlock_device.html", success=generic_ok)

    # Create one-time unlock token (1 hour)
    token = secrets.token_urlsafe(32)
    expires = (dt.datetime.now() + dt.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    persistence.set_password_token(token, {
        "email": email,
        "key": key,
        "expires_at": expires,
        "purpose": "device_unlock",
    })
    unlock_url = request.url_root.rstrip("/") + url_for("confirm_unlock_device", token=token)
    name = info.get("customer_name") or "there"
    sent = notifications.send_device_unlock_email(email, name, unlock_url)
    if not sent:
        # Still show generic; log for admin
        app.logger.warning(f"Device unlock email failed for {email} key={key[:12]}…")
    persistence.append_audit("device_unlock_requested", f"{email} key={key[:16]}…", actor=email)
    return render_template("unlock_device.html", success=generic_ok)


@app.route("/unlock-device/confirm/<token>", methods=["GET"])
def confirm_unlock_device(token):
    """One-time link from email: clear device lock on the key."""
    record = persistence.get_password_token(token)
    if not record or record.get("purpose") != "device_unlock":
        return render_template("unlock_device.html", error="This unlock link is invalid or has already been used.")
    try:
        exp = dt.datetime.strptime(record.get("expires_at", ""), "%Y-%m-%d %H:%M:%S")
        if dt.datetime.now() > exp:
            persistence.delete_password_token(token)
            return render_template("unlock_device.html", error="This unlock link has expired. Request a new one.")
    except ValueError:
        persistence.delete_password_token(token)
        return render_template("unlock_device.html", error="This unlock link is invalid.")

    key = record.get("key", "")
    ok = licensing.reset_device_lock(key)
    persistence.delete_password_token(token)  # single-use
    if not ok:
        return render_template("unlock_device.html", error="Could not unlock that key. Contact support.")
    persistence.append_audit("device_unlock_confirmed", f"key={key[:16]}…", actor=record.get("email", ""))
    return render_template(
        "unlock_device.html",
        success=(
            "Device lock cleared. On this device, open Activate, enter your license key, "
            "and you should be good to go."
        ),
        show_activate=True,
    )


@app.route("/admin/audit")
@admin_required
def admin_audit():
    rows = persistence.load_audit_log(200)
    return render_template("admin/audit.html", rows=rows)


@app.route("/api/announcements")
def api_announcements():
    """Public, unauthenticated — the bell dropdown and top banner fetch
    this on every page load. Deliberately returns only the fields the
    frontend needs, not the raw DB rows.

    BUG FIX: this never set Cache-Control, so a browser could legitimately
    serve a stale cached copy of this GET response on a later page load —
    e.g. testing Free, then activating Pro on the SAME device/browser
    minutes later, could still show the old response. Explicit no-store
    guarantees every page load gets the current announcement list."""
    live = persistence.load_active_announcements()
    resp = jsonify([{
        "id": a["id"],
        "type": a.get("type", "update"),
        "title": a.get("title", ""),
        "message": a.get("message", ""),
        "link_url": a.get("link_url", ""),
        "link_text": a.get("link_text", "Learn more"),
        "banner": bool(a.get("banner")),
        "created": a.get("created", ""),
    } for a in live])
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/ads.txt")
def ads_txt():
    """AdSense site-verification / IAB ads.txt. Defaults to Faisal's actual
    publisher ID so this works even if ADSENSE_PUBLISHER_ID isn't set on
    the server — that env-var gap is what caused AdSense to report
    'Not found' on Aug 7, 2026. Still override-able via env var if the
    publisher ID ever needs to change without a code deploy.
    Must be served at the domain root, exactly at /ads.txt — Google checks
    this exact path, not /static/ads.txt.
    """
    pub_id = os.environ.get("ADSENSE_PUBLISHER_ID", "pub-3088581560119805")
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

    # Try both product lines: this one freemius_license_id will only ever
    # match a record in ONE of them (browser Pro/Pro+ license vs. Developer
    # API key), so the other call is always a harmless not_an_api_key /
    # no-op — cheaper than branching on plan_id here to guess which one,
    # and keeps this webhook the single place both products stay in sync
    # on cancellation/renewal without any admin action.
    app_result = licensing.sync_license_from_freemius_event(freemius_license_id, event_type, new_expiration)
    api_result = api_keys.sync_key_from_freemius_event(freemius_license_id, event_type)
    success = app_result.get("success") or api_result.get("success")
    return jsonify({"app_license": app_result, "api_key": api_result}), (200 if success else 404)


def _provision_paid_account(email: str, name: str, product_label: str):
    """Shared by fs_callback, fs_callback_api, and the manual /upgrade
    admin approval below — the three places a customer becomes a paying
    customer. Creates the account if one doesn't exist yet (idempotent —
    a renewal or a second purchase just returns the existing account
    untouched) and, ONLY for a brand-new account, emails a 'set your
    password' link. Never called from the free tier (self-serve API
    signup, free voices) by design — those stay accountless."""
    email = (email or "").strip()
    if not email or "@" not in email:
        return
    record, is_new = accounts.find_or_create_user(email, name)
    if is_new:
        token = accounts.issue_token(email, "set")
        set_url = request.url_root.rstrip("/") + url_for("set_password", token=token)
        notifications.send_account_setup_email(email, record.get("name", name), set_url, product_label)


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
        # BUG FIX: this used to hardcode subscription_type="monthly" (a
        # blind 30-day expiry) regardless of what the customer actually
        # bought. Freemius already knows the real billing cycle — verify_result
        # carries its actual `expires_at` — so an annual purchase was getting
        # cut off after 30 days instead of a year, until the next webhook
        # happened to correct it (which for an annual plan could be
        # ~11 months away). Passing that real expiry through directly fixes
        # both monthly and annual the same way, with no separate code path.
        license_key = licensing.create_subscription_key(
            customer_name=verify_result.get("customer_name") or "Pro User",
            customer_email=verify_result.get("customer_email") or fs_email,
            subscription_type="recurring",
            expires_at=verify_result.get("expires_at", ""),
            freemius_license_id=fs_license_id,
            amount_paid=limits.get("PRO_PRICE_PKR", 0),
            plan=verify_result.get("plan", "pro"),
        )

    _provision_paid_account(
        verify_result.get("customer_email") or fs_email,
        verify_result.get("customer_name") or "Pro User",
        "VoxCraft Pro+" if verify_result.get("plan") == "pro_plus" else "VoxCraft Pro",
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


@app.route("/fs-callback/api")
def fs_callback_api():
    """The Developer API's equivalent of fs_callback — where a customer's
    browser lands after paying for API Starter or API Pro through Freemius.
    Verifies the license, mints (or reuses, if they refresh this page) an
    API key, emails it, and shows it once inline. This is the piece that
    makes the paid side of the API actually self-serve: previously a
    payment here still required Faisal to manually create the key in
    /admin/api-keys afterward — now that step is gone for the Starter/Pro
    tiers specifically (Custom/negotiated plans still go through admin).

    Requires a SECOND Freemius checkout link setup step, same as Pro+: in
    Freemius, the API Starter and API Pro plans each need their own
    checkout link configured to redirect here (?license_id=X&email=Y) after
    purchase, same as /fs-callback is for the app's Pro/Pro+ plans."""
    fs_license_id = request.args.get("license_id", "")
    fs_email = request.args.get("email", "")

    if not fs_license_id:
        return render_template("fs_callback_api.html", error="no_license_id")

    lim = persistence.load_limits()
    verify_result = licensing.verify_freemius_api_license(
        fs_license_id,
        api_starter_quota=int(lim.get("API_STARTER_QUOTA", 200000)),
        api_pro_quota=int(lim.get("API_PRO_QUOTA", 1000000)),
    )

    if not verify_result.get("valid"):
        return render_template("fs_callback_api.html", error="not_verified",
                                license_id=fs_license_id,
                                verify_error=verify_result.get("error", "unknown"))

    # Idempotent: if this Freemius license already minted a key (e.g. the
    # customer refreshed this page), don't mint a second one — the raw key
    # can't be shown again, so just confirm it was already sent.
    existing = api_keys.find_key_by_freemius_id(fs_license_id)
    if existing:
        _provision_paid_account(existing.get("customer_email", fs_email), existing.get("customer_name", "API Customer"),
                                 f"VoxCraft Developer API — {existing.get('plan', 'api')}")
        return render_template("fs_callback_api.html", success=True, already_issued=True,
                                customer_email=existing.get("customer_email", fs_email),
                                plan=existing.get("plan"), quota=existing.get("monthly_char_quota"))

    plan = verify_result["plan"]
    quota = verify_result["quota"]
    customer_email = verify_result.get("customer_email") or fs_email
    customer_name = verify_result.get("customer_name") or "API Customer"

    result = api_keys.create_api_key(customer_name, customer_email, plan, quota,
                                      freemius_license_id=fs_license_id)
    sent = notifications.send_api_key_email(customer_email, customer_name, result["raw_key"], plan, quota)
    if not sent:
        app.logger.warning(f"Auto-issued API key for {customer_email} but email delivery failed.")

    _provision_paid_account(customer_email, customer_name, f"VoxCraft Developer API — {plan}")

    return render_template("fs_callback_api.html", success=True, raw_key=result["raw_key"],
                            plan=plan, quota=quota, customer_email=customer_email)


CUSTOMER_LOGIN_MAX_ATTEMPTS = 8
CUSTOMER_LOGIN_WINDOW_MINUTES = 15
CUSTOMER_LOGIN_LOCKOUT_MINUTES = 15


def account_required(view_func):
    from functools import wraps

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("account_email"):
            return redirect(url_for("account_login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapper


@app.route("/login", methods=["GET", "POST"])
def account_login():
    """Paid-customer login — separate from /admin/login above, and
    deliberately not the source of truth for Pro/API access (see
    accounts.py's docstring): this just looks up and hands back whatever
    key(s) licensing.py/api_keys.py already have on file for the email.
    No 'sign up' link here on purpose — accounts only exist because a
    payment created one (see _provision_paid_account)."""
    if request.method == "GET":
        return render_template("account_login.html")

    ip_hash = "login:" + usage_tracking.hash_ip(usage_tracking.get_client_ip(request))
    now = dt.datetime.now()
    record = persistence.get_login_attempts(ip_hash)

    locked_until_str = record.get("locked_until")
    if locked_until_str:
        locked_until = dt.datetime.strptime(locked_until_str, "%Y-%m-%d %H:%M:%S")
        if now < locked_until:
            remaining_min = max(1, int((locked_until - now).total_seconds() // 60) + 1)
            return render_template("account_login.html",
                                    error=f"Too many failed attempts. Try again in {remaining_min} minute(s).")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    user = accounts.verify_login(email, password)

    if user:
        persistence.clear_login_attempts(ip_hash)
        session["account_email"] = user["email"]
        next_url = request.args.get("next") or url_for("account_dashboard")
        return redirect(next_url)

    first_attempt_str = record.get("first_attempt")
    if first_attempt_str:
        first_attempt = dt.datetime.strptime(first_attempt_str, "%Y-%m-%d %H:%M:%S")
        if (now - first_attempt).total_seconds() > CUSTOMER_LOGIN_WINDOW_MINUTES * 60:
            record = {}
    count = record.get("count", 0) + 1
    new_record = {"count": count, "first_attempt": record.get("first_attempt", now.strftime("%Y-%m-%d %H:%M:%S"))}
    if count >= CUSTOMER_LOGIN_MAX_ATTEMPTS:
        new_record["locked_until"] = (now + dt.timedelta(minutes=CUSTOMER_LOGIN_LOCKOUT_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    persistence.set_login_attempts(ip_hash, new_record)

    if count >= CUSTOMER_LOGIN_MAX_ATTEMPTS:
        return render_template("account_login.html",
                                error=f"Too many failed attempts. Try again in {CUSTOMER_LOGIN_LOCKOUT_MINUTES} minutes.")
    # Deliberately identical whether the email doesn't exist, has no
    # password set yet, or the password is wrong — so this can't be used
    # to check which emails are customers.
    return render_template("account_login.html", error="Incorrect email or password.")


@app.route("/logout")
def account_logout():
    session.pop("account_email", None)
    return redirect(url_for("landing"))


@app.route("/account")
@account_required
def account_dashboard():
    email = session["account_email"]
    user = accounts.find_user(email)
    license_key = licensing.find_key_by_email(email)
    license_info = licensing.check_vox_license(license_key) if license_key else {"valid": False}
    api_key_records = api_keys.find_keys_by_email(email)
    return render_template("account.html", user=user, license_key=license_key,
                            license_info=license_info, api_key_records=api_key_records)


@app.route("/account/rotate-api-key", methods=["POST"])
@account_required
def account_rotate_api_key():
    """Customer-initiated key rotation from their own dashboard — old key
    stops working immediately, new one is emailed the same way a freshly
    issued key is. Only allowed on a key that's actually theirs, checked
    by email match rather than trusting the posted key_id blindly."""
    email = session["account_email"]
    key_id = request.form.get("key_id", "")
    owned = [k for k in api_keys.find_keys_by_email(email) if str(k["id"]) == key_id]
    if not owned:
        return redirect(url_for("account_dashboard"))
    result = api_keys.rotate_key(key_id)
    if result:
        notifications.send_api_key_email(email, owned[0].get("customer_name", "Customer"),
                                          result["raw_key"], result["record"]["plan"],
                                          result["record"]["monthly_char_quota"])
    return redirect(url_for("account_dashboard"))


@app.route("/set-password/<token>", methods=["GET", "POST"])
def set_password(token):
    """Handles the initial 'welcome, set your password' link sent by
    _provision_paid_account. GET only PEEKS at the token (doesn't mark it
    used) — email clients and security scanners routinely pre-fetch links
    via GET, and a single-use token consumed by that automated fetch
    would lock the real customer out before they ever clicked it. Only
    the actual POST (submitting the password) consumes it, mirroring
    reset_password below."""
    if request.method == "GET":
        record = persistence.get_password_token(token)
        if not record or record.get("used") or record.get("purpose") != "set":
            return render_template("set_password.html", error="This link is invalid or has expired.", mode="set")
        try:
            expired = dt.datetime.fromisoformat(record["expires_at"]) < dt.datetime.now()
        except Exception:
            expired = True
        if expired:
            return render_template("set_password.html", error="This link is invalid or has expired.", mode="set")
        return render_template("set_password.html", email=record["email"], mode="set", token=token)

    token_info = accounts.consume_token(token)
    if not token_info or token_info.get("purpose") != "set":
        return render_template("set_password.html", error="This link is invalid or has expired.", mode="set")
    password = request.form.get("password", "")
    if len(password) < 8:
        return render_template("set_password.html", email=token_info["email"], mode="set", token=token,
                                error="Password must be at least 8 characters.")
    accounts.set_password(token_info["email"], password)
    session["account_email"] = token_info["email"]
    return redirect(url_for("account_dashboard"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot_password.html")
    email = request.form.get("email", "").strip().lower()
    user = accounts.find_user(email)
    if user:
        token = accounts.issue_token(email, "reset")
        reset_url = request.url_root.rstrip("/") + url_for("reset_password", token=token)
        notifications.send_password_reset_email(email, user.get("name", "Customer"), reset_url)
    # Same message whether or not the email has an account — avoids
    # confirming to an outside guesser which emails are paying customers.
    return render_template("forgot_password.html", submitted=True)


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if request.method == "GET":
        record = persistence.get_password_token(token)
        if not record or record.get("used") or record.get("purpose") != "reset":
            return render_template("set_password.html", error="This link is invalid or has expired.", mode="reset")
        try:
            expired = dt.datetime.fromisoformat(record["expires_at"]) < dt.datetime.now()
        except Exception:
            expired = True
        if expired:
            return render_template("set_password.html", error="This link is invalid or has expired.", mode="reset")
        return render_template("set_password.html", email=record["email"], mode="reset", token=token)

    token_info = accounts.consume_token(token)
    if not token_info or token_info.get("purpose") != "reset":
        return render_template("set_password.html", error="This link is invalid or has expired.", mode="reset")
    password = request.form.get("password", "")
    if len(password) < 8:
        return render_template("set_password.html", email=token_info["email"], mode="reset", token=token,
                                error="Password must be at least 8 characters.")
    accounts.set_password(token_info["email"], password)
    session["account_email"] = token_info["email"]
    return redirect(url_for("account_dashboard"))


@app.route("/tools")
def tools_hub():
    """Directory page — lists all 8 tools as preview cards linking to their
    own dedicated /tools/<slug> page, which is where the actual widget
    lives now. Previously this page embedded every tool's full working
    widget itself (behind tabs), which meant a visitor's need was already
    met right here — nobody had a reason to click through to the richer,
    more indexable dedicated pages that actually rank in search. Directory
    + dedicated-page-does-the-work keeps each tool's functionality in
    exactly one place (the tool_widgets partials, unchanged) while giving
    search traffic a real reason to land on, and stay on, the specific
    page that matches their query."""
    ordered_tools = [dict(slug=s, **tool_pages.TOOL_PAGES[s]) for s in tool_pages.TOOL_ORDER]
    return render_template("tools.html", ordered_tools=ordered_tools,
                            filedesk_url=os.environ.get("FILEDESK_URL", "").strip())


@app.route("/tools/<slug>")
def tool_page(slug):
    """Each tool's own indexable page — full write-up (how it works, use
    cases, tips, FAQ) plus the same widget used on the /tools hub, via the
    shared partials/tool_widgets/ include. See tool_pages.py for why this
    exists: individual URLs with real content instead of one tabbed page
    with almost no unique text per tool."""
    tool = tool_pages.TOOL_PAGES.get(slug)
    if not tool:
        return render_template("404.html") if os.path.exists(os.path.join(app.root_path, "templates", "404.html")) \
            else (f"Tool '{slug}' not found.", 404)

    related_tools = [dict(slug=s, **tool_pages.TOOL_PAGES[s]) for s in tool.get("related_tools", [])
                      if s in tool_pages.TOOL_PAGES]

    # Related blog posts: cheap keyword match against title/category/excerpt
    # so each tool page pulls in relevant articles without hand-maintaining
    # a per-tool post list that goes stale as new posts get published.
    related_posts = []
    keywords = [k.lower() for k in tool.get("blog_keywords", [])]
    if keywords:
        for post in persistence.load_blogs():
            if not _blog_is_public(post):
                continue
            haystack = f"{post.get('title', '')} {post.get('category', '')} {post.get('excerpt', '')}".lower()
            if any(k in haystack for k in keywords):
                related_posts.append(post)
        related_posts = related_posts[:3]
        for _rp in related_posts:
            _rp["_slug"] = _blog_slug(_rp)

    # A couple of the content strings above reference other tool/page URLs
    # via {placeholder} tokens — fill them in here rather than hardcoding
    # url_for() calls inside tool_pages.py, which doesn't have app context.
    url_map = {
        "denoise_url": url_for("tool_page", slug="remove-background-noise"),
        "cutter_url": url_for("tool_page", slug="trim-cut-audio"),
        "transcribe_url": url_for("tool_page", slug="transcribe-audio-to-text"),
        "privacy_url": url_for("privacy"),
        "upgrade_url": url_for("upgrade"),
        "voiceclone_url": url_for("voice_cloning"),
    }
    tool = dict(tool)
    tool["intro"] = [p.format(**url_map) for p in tool.get("intro", [])]
    tool["tips"] = [t.format(**url_map) for t in tool.get("tips", [])]
    tool["use_cases"] = [(n, d.format(**url_map)) for n, d in tool.get("use_cases", [])]
    tool["faq"] = [(q, a.format(**url_map)) for q, a in tool.get("faq", [])]

    return render_template("tool_page.html", tool=tool, related_tools=related_tools, related_posts=related_posts,
                            lang_options=audio_tools.LANG_OPTIONS, usage=usage_summary())


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
        return jsonify({"error": f"Free plan allows up to {char_limit_widget:,} characters per generation. Shorten the script, or upgrade for unlimited length."}), 429

    if _would_exceed_monthly_quota(len(text), lim["FREE_MONTHLY_CHAR_QUOTA"]):
        return jsonify({"error": f"Monthly free quota ({lim['FREE_MONTHLY_CHAR_QUOTA']:,} characters) is used up. It resets next month — or upgrade for unlimited."}), 429

    if not _under_limit("usage_singles", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Daily free limit reached ({lim['FREE_DAILY_ACTIONS']} generations/day). Resets at midnight UTC — or upgrade for unlimited."}), 429

    rate_str = f"{speed_pct - 100:+d}%"
    text = apply_pronunciation_dict(text, persistence.load_pronunciation_dict())
    try:
        audio = tts_dispatch(text, voice_id, rate=rate_str, ssml_mode=ssml_mode, speed_pct=speed_pct)
    except Exception as e:
        # Don't leak internal stack traces to the client
        return jsonify({"error": "Could not generate audio right now. Please try again in a moment."}), 500

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
    pron_dict = persistence.load_pronunciation_dict()  # loaded once per batch, not once per line

    for idx, line in enumerate(lines):
        try:
            audio = tts_dispatch(apply_pronunciation_dict(line, pron_dict), voice_id, rate=rate_str, speed_pct=speed_pct)
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


# ---------------------------------------------------------------------------
# Public developer API (/api/v1/...) — the paid, metered API product.
# Distinct from every /api/... route above: those are called by VoxCraft's
# own frontend JS using session/CSRF auth; these are called by external
# developers' own code using a Bearer API key. See api_keys.py for the
# full design rationale (fixed monthly quota rather than true metered
# billing, hashed-at-rest keys, the concurrency-safe usage counter).
# ---------------------------------------------------------------------------
API_MAX_CHARS_PER_REQUEST = 5000  # generous single-request cap — mainly to stop one oversized request from being the ONLY thing standing between a customer and their whole month's quota in one shot


def _api_v1_authenticate():
    """Returns (record, error_response_or_None). Shared by every /api/v1/
    route so auth/active-check logic lives in exactly one place."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, (jsonify({"error": "Missing or malformed Authorization header. Expected: Bearer <api_key>"}), 401)
    raw_key = auth_header[len("Bearer "):].strip()
    record = api_keys.find_key_record(raw_key)
    if not record:
        return None, (jsonify({"error": "Invalid API key."}), 401)
    if not record.get("active", True):
        return None, (jsonify({"error": "This API key has been revoked."}), 403)
    return record, None


@app.route("/api/v1/voices", methods=["GET"])
def api_v1_voices():
    """Lets a developer discover valid voice_id values without needing to
    read separate docs first — small addition, meaningfully better
    first-run experience. Requires a valid key (even though the data
    itself isn't sensitive) so an unauthenticated key-tester can't be used
    as a free discovery/scraping endpoint."""
    record, err = _api_v1_authenticate()
    if err:
        return err
    return jsonify({
        "voices": [
            {"language": lang, "name": name, "voice_id": vid}
            for lang, voice_map in VOICES.items()
            for name, vid in voice_map.items()
        ]
    })


@app.route("/api/v1/tts", methods=["POST"])
def api_v1_tts():
    """POST { "text": "...", "voice_id": "en-US-AvaNeural", "rate": "+0%" }
    Header: Authorization: Bearer <api_key>
    Returns: audio/mpeg binary on success, JSON error otherwise.

    Deducts from the key's monthly character quota only on SUCCESSFUL
    generation — mirrors the browser-side _bump_monthly_chars() pattern,
    for the same reason: a customer shouldn't pay quota for a request
    that failed on VoxCraft's end (a bad voice_id, an engine error)."""
    record, err = _api_v1_authenticate()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    voice_id = (data.get("voice_id") or "").strip()
    rate = (data.get("rate") or "+0%").strip()

    if not text:
        return jsonify({"error": "'text' is required."}), 400
    if len(text) > API_MAX_CHARS_PER_REQUEST:
        return jsonify({"error": f"'text' exceeds the {API_MAX_CHARS_PER_REQUEST}-character limit per request. Split into multiple calls."}), 400
    if not voice_id:
        return jsonify({"error": "'voice_id' is required. See GET /api/v1/voices for valid values."}), 400

    valid_voice_ids = {vid for voice_map in VOICES.values() for vid in voice_map.values()}
    if voice_id not in valid_voice_ids:
        return jsonify({"error": f"Unknown voice_id '{voice_id}'. See GET /api/v1/voices for valid values."}), 400

    if api_keys.would_exceed_quota(record, len(text)):
        usage = api_keys.get_usage(record["key_hash"])
        return jsonify({
            "error": "Monthly character quota exceeded for this API key.",
            "quota": record["monthly_char_quota"],
            "used_this_period": usage["chars_used"],
        }), 429

    processed_text = apply_pronunciation_dict(text, persistence.load_pronunciation_dict())
    try:
        audio = tts_dispatch(processed_text, voice_id, rate=rate)
    except Exception as e:
        return jsonify({"error": f"Generation failed: {str(e)}"}), 500

    api_keys.bump_usage(record["key_hash"], len(text))
    usage_after = api_keys.get_usage(record["key_hash"])

    resp = send_file(io.BytesIO(audio), mimetype="audio/mpeg", download_name="speech.mp3")
    # Standard-shaped rate-limit headers — not enforced here (quota is
    # already enforced above), just informational so a developer's own
    # client code can proactively back off before hitting 429.
    resp.headers["X-Quota-Limit"] = str(record["monthly_char_quota"])
    resp.headers["X-Quota-Used"] = str(usage_after["chars_used"])
    resp.headers["X-Quota-Remaining"] = str(max(0, record["monthly_char_quota"] - usage_after["chars_used"]))
    return resp


@app.route("/api/clone/upload", methods=["POST"])
def api_clone_upload():
    """Pro+-only: upload a reference clip (~10s+) to clone a voice from.
    TODO: this saves to /tmp, which is wiped on every VPS redeploy/restart —
    fine for a same-session clone-then-generate flow, but if you want cloned
    voices to persist across sessions, save the reference clip to your
    GitHub-persisted storage (same pattern as your other config data) instead.
    """
    if not has_clone_and_music():
        return jsonify({"error": "Voice cloning is a Pro+ feature."}), 402

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


@app.route("/api/clone/voices/save", methods=["POST"])
def api_clone_voice_save():
    """Pro+-only: permanently save a just-uploaded reference clip as a
    reusable voice, gated on the customer explicitly checking the consent
    popup (they own/have permission for this voice and license it to us).
    Without consent == true this refuses outright — no partial save."""
    if not has_clone_and_music():
        return jsonify({"error": "Voice cloning is a Pro+ feature."}), 402

    license_key = session.get("license_key")
    if not license_key:
        return jsonify({"error": "Session expired — please re-activate your license."}), 401

    data = request.get_json(force=True) or {}
    reference_id = data.get("reference_id")
    name = (data.get("name") or "").strip()
    consent = data.get("consent") is True
    ref_text = (data.get("ref_text") or "").strip()[:300]

    if not reference_id:
        return jsonify({"error": "Upload a reference clip first."}), 400
    if not name:
        return jsonify({"error": "Give this voice a name."}), 400
    if not consent:
        return jsonify({"error": "You must confirm the consent statement to save a voice."}), 400

    src_path = os.path.join(CLONE_UPLOAD_DIR, reference_id)
    if not os.path.exists(src_path):
        return jsonify({"error": "Reference clip not found — please re-upload."}), 400

    if persistence.count_voices_for_license(license_key) >= MAX_SAVED_VOICES_PER_LICENSE:
        return jsonify({"error": f"You can save up to {MAX_SAVED_VOICES_PER_LICENSE} voices. Delete one first."}), 400

    import uuid
    import shutil
    ext = os.path.splitext(reference_id)[1].lower() or ".wav"
    voice_id = uuid.uuid4().hex
    dest_filename = f"{voice_id}{ext}"
    dest_path = os.path.join(VOICE_REFS_DIR, dest_filename)
    shutil.copy2(src_path, dest_path)

    now_iso = dt.datetime.utcnow().isoformat() + "Z"
    persistence.save_voice(voice_id, license_key, {
        "name": name[:80],
        "filename": dest_filename,
        "created_at": now_iso,
        "ref_text": ref_text,
    })

    # Permanent, never-pruned evidence trail — kept even if the voice is
    # later deleted by the customer.
    ip_hash = usage_tracking.hash_ip(usage_tracking.get_client_ip(request))
    persistence.record_voice_consent({
        "voice_id": voice_id,
        "license_key": license_key,
        "ip_hash": ip_hash,
        "consented_at": now_iso,
        "consent_version": VOICE_CONSENT_VERSION,
        "consent_text": VOICE_CONSENT_TEXT,
    })

    return jsonify({"id": voice_id, "name": name[:80], "created_at": now_iso})


@app.route("/api/clone/voices", methods=["GET"])
def api_clone_voices_list():
    """Pro+-only: list the current license's saved voices for a picker UI."""
    if not has_clone_and_music():
        return jsonify({"error": "Voice cloning is a Pro+ feature."}), 402
    license_key = session.get("license_key")
    if not license_key:
        return jsonify({"error": "Session expired — please re-activate your license."}), 401

    voices = persistence.load_voices_for_license(license_key)
    return jsonify({
        "voices": [
            {
                "id": v["id"],
                "name": v.get("name", "Untitled voice"),
                "created_at": v.get("created_at", ""),
                "ref_text": v.get("ref_text", ""),
            }
            for v in voices
        ]
    })


@app.route("/api/clone/voices/<voice_id>", methods=["DELETE"])
def api_clone_voice_delete(voice_id):
    """Pro+-only: delete a saved voice. Ownership-checked — deleting someone
    else's voice_id (or a stale/mistyped one) is a no-op 404, not a leak."""
    if not has_clone_and_music():
        return jsonify({"error": "Voice cloning is a Pro+ feature."}), 402
    license_key = session.get("license_key")
    if not license_key:
        return jsonify({"error": "Session expired — please re-activate your license."}), 401

    voice = persistence.get_voice(voice_id)
    if not voice or voice.get("license_key") != license_key:
        return jsonify({"error": "Saved voice not found."}), 404

    deleted = persistence.delete_voice(voice_id, license_key)
    if deleted:
        path = os.path.join(VOICE_REFS_DIR, voice["filename"])
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass  # DB row is already gone; an orphaned file isn't harmful, just wasted disk
    return jsonify({"deleted": deleted})


@app.route("/api/clone/generate", methods=["POST"])
def api_clone_generate():
    if not has_clone_and_music():
        return jsonify({"error": "Voice cloning is a Pro+ feature."}), 402

    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    reference_id = data.get("reference_id")
    saved_voice_id = data.get("saved_voice_id")
    language_id = (data.get("language_id") or "en").strip().lower()
    engine = (data.get("engine") or "chatterbox").strip().lower()

    if not text:
        return jsonify({"error": "Please enter some text first."}), 400
    if len(text) > CLONE_CHAR_LIMIT:
        return jsonify({"error": f"Cloned-voice generations are capped at {CLONE_CHAR_LIMIT} characters."}), 400
    if not reference_id and not saved_voice_id:
        return jsonify({"error": "Upload a reference clip or pick a saved voice first."}), 400
    if engine not in modal_client.VALID_ENGINES:
        return jsonify({"error": f"Unknown engine '{engine}'."}), 400

    if saved_voice_id:
        voice = persistence.get_voice(saved_voice_id)
        license_key = session.get("license_key")
        if not voice or voice.get("license_key") != license_key:
            return jsonify({"error": "Saved voice not found."}), 404
        path = os.path.join(VOICE_REFS_DIR, voice["filename"])
        if not os.path.exists(path):
            return jsonify({"error": "Saved voice's audio file is missing — please re-save it."}), 400
    else:
        path = os.path.join(CLONE_UPLOAD_DIR, reference_id)
        if not os.path.exists(path):
            return jsonify({"error": "Reference clip not found — please re-upload."}), 400

    # Language ID is passed through to clone_engine, which handles
    # Urdu transliteration internally via urdu_transliteration.prepare_text_for_tts().
    # The Modal worker only accepts "en" or "hi" — clone_engine resolves this.
    if language_id not in ("en", "hi", "ur"):
        language_id = "en"

    ref_text = (data.get("ref_text") or "").strip()
    # If the caller didn't type one this time but the saved voice already
    # has a ref_text attached from when it was saved, reuse it — this is
    # what makes ref_text "cached" per voice instead of needing retyping
    # on every generation.
    if not ref_text and saved_voice_id:
        ref_text = (voice.get("ref_text") or "").strip()

    try:
        job_id = start_clone_job(
            text,
            path,
            language_id=language_id,
            engine=engine,
            ref_text=ref_text,
        )
    except Exception as e:
        import traceback
        return jsonify({"error": f"Failed to start clone job: {str(e)}", "detail": traceback.format_exc()}), 500

    if not job_id:
        return jsonify({"error": "Failed to create clone job — no job ID returned."}), 500

    return jsonify({"job_id": job_id})


@app.route("/api/clone/status/<job_id>")
def api_clone_status(job_id):
    if not job_id or not isinstance(job_id, str):
        return jsonify({"error": "Invalid job ID."}), 400

    job = get_job(job_id)
    if not job:
        # BUG FIX: "Unknown job." was too vague. Distinguish between:
        # - Job never existed (bad ID from frontend)
        # - Job expired/cleaned up (normal for old jobs)
        # - Job exists on a different worker (gunicorn multi-worker issue)
        return jsonify({
            "error": "Job not found. It may have expired, been cleaned up, or the job ID is invalid. Please try generating again."
        }), 404

    if job["status"] == "done":
        return jsonify({
            "status": "done",
            "audio_b64": base64.b64encode(job["audio"]).decode("ascii"),
            "chunks_generated": job.get("chunks_generated", 1),
            "duration_seconds": job.get("duration_seconds", 0.0)
        })
    if job["status"] == "error":
        return jsonify({
            "status": "error",
            "error": job.get("error", "Unknown error during voice cloning."),
            "detail": job.get("error_detail", "")
        })
    return jsonify({
        "status": job["status"],
        "progress": job.get("progress", 0),
        "message": job.get("message", "Processing...")
    })


# ---------------------------------------------------------------------------
# Music generation (Replicate-hosted ACE-Step) — Pro+-only, real $ cost per run
# ---------------------------------------------------------------------------
MUSIC_MAX_DURATION_SEC = 120  # keep runs (and cost) bounded — tune in admin later if you add a limits field


@app.route("/api/music/generate", methods=["POST"])
def api_music_generate():
    if not has_clone_and_music():
        return jsonify({"error": "Music generation is a Pro+ feature."}), 402

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
