"""
VoxCraft — Flask app.

This pass: real licensing (internal keys + Freemius), IP-based usage tracking,
manual pro-request queue, admin panel, ads, blog, and privacy/terms/contact
pages — ported from your Streamlit app's backend modules (see persistence.py,
licensing.py, usage_tracking.py, notifications.py, pro_requests.py).

Still NOT ported: Music tool, Denoise, Voice Changer, Video-to-Audio extractor.
Paddle is intentionally NOT ported (Freemius replaced it per your own history).

REQUIRED ENV VARS for this pass to actually work (see README):
- GITHUB_TOKEN      — repo-scope PAT for faisalchaudhary411/faisalchaudhary411.github.io
- ADMIN_PASSWORD    — gates /admin (there was NO auth on the original admin page — added here)
- RESEND_API_KEY, ADMIN_EMAIL — for pro-request notification emails
- FREEMIUS_API_TOKEN, FREEMIUS_PRODUCT_ID — only if you want Freemius checkout wired live
"""

from flask import Flask, render_template, request, jsonify, session, send_file, redirect, url_for, flash
import os
import io
import time
import zipfile
import base64
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
from werkzeug.utils import secure_filename

CLONE_UPLOAD_DIR = "/tmp/voxcraft_clone_refs"
os.makedirs(CLONE_UPLOAD_DIR, exist_ok=True)
CLONE_CHAR_LIMIT = 500  # tighter than normal TTS — keeps CPU generation time bounded

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

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
    return {"is_pro_ctx": is_pro()}


def _today() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d")


def _this_month() -> str:
    return dt.datetime.now().strftime("%Y-%m")


def _reset_daily_if_needed():
    if session.get("usage_date") != _today():
        session["usage_date"] = _today()
        session["usage_singles"] = 0
        session["usage_batches"] = 0
        session["usage_previews"] = 0
        session["usage_transcribe"] = 0
        session["usage_convert"] = 0
        session["usage_merge"] = 0
        session["usage_cutter"] = 0
        session["usage_denoise"] = 0
        session["usage_voicechange"] = 0
        session["usage_videoxtract"] = 0


def _reset_monthly_if_needed():
    """Separate from the daily reset above — BUG FIX: the character quota is
    meant to be a monthly budget (matches what it's actually labeled as
    everywhere: 'chars/generation' is the per-request cap, but the usage bar
    showing a running total was being reset DAILY alongside the daily action
    counters, comparing a daily-reset number against what's really meant to
    be a much longer-period allowance. Chars now track and reset on their own
    monthly cycle, independent of the daily counters."""
    if session.get("usage_month") != _this_month():
        session["usage_month"] = _this_month()
        session["usage_chars_monthly"] = 0


def _check_and_bump(counter_key: str, limit: int) -> bool:
    """Returns True if under limit (and increments), False if limit hit."""
    _reset_daily_if_needed()
    if is_pro():
        return True
    current = session.get(counter_key, 0)
    if current >= limit:
        return False
    session[counter_key] = current + 1
    return True


def _monthly_chars_used() -> int:
    _reset_monthly_if_needed()
    return session.get("usage_chars_monthly", 0)


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
    _reset_monthly_if_needed()
    session["usage_chars_monthly"] = session.get("usage_chars_monthly", 0) + char_count


@app.route("/")
def landing():
    return render_template("landing.html")


def usage_summary() -> dict:
    """Surfaces the SAME counters that _check_and_bump / _check_monthly_chars
    actually enforce — this is deliberately the session-cookie numbers, not
    usage_tracking.py's IP-based numbers, so what's displayed always matches
    what's enforced. Limits themselves come from get_limits() (GitHub-backed,
    editable in /admin/limits).
    (Note: usage_tracking.py's IP-based module exists for licensing checks
    but isn't wired into daily-limit enforcement here — see README.)"""
    _reset_daily_if_needed()
    _reset_monthly_if_needed()
    lim = get_limits()
    return {
        "singles": {"used": session.get("usage_singles", 0), "limit": lim["FREE_DAILY_ACTIONS"]},
        "chars_monthly": {"used": session.get("usage_chars_monthly", 0), "limit": lim["FREE_MONTHLY_CHAR_QUOTA"]},
        "batches": {"used": session.get("usage_batches", 0), "limit": lim["FREE_BATCH_LIMIT"]},
        "previews": {"used": session.get("usage_previews", 0), "limit": lim["FREE_PREVIEW_LIMIT"]},
        "transcribe": {"used": session.get("usage_transcribe", 0), "limit": lim["FREE_DAILY_ACTIONS"]},
        "convert": {"used": session.get("usage_convert", 0), "limit": lim["FREE_DAILY_ACTIONS"]},
        "merge": {"used": session.get("usage_merge", 0), "limit": lim["FREE_DAILY_ACTIONS"]},
        "cutter": {"used": session.get("usage_cutter", 0), "limit": lim["FREE_DAILY_ACTIONS"]},
        "denoise": {"used": session.get("usage_denoise", 0), "limit": lim["FREE_DAILY_ACTIONS"]},
        "voicechange": {"used": session.get("usage_voicechange", 0), "limit": lim["FREE_DAILY_ACTIONS"]},
        "videoxtract": {"used": session.get("usage_videoxtract", 0), "limit": lim["FREE_DAILY_ACTIONS"]},
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
         "cta_url": limits.get("CHECKOUT_URL") or url_for("upgrade")},
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
        return render_template("upgrade.html", checkout_url=checkout_url)
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

    result = pro_requests.submit_pro_request(request, name, email, phone, payment_method, txn_id, screenshot_b64)
    if result.get("success"):
        if result.get("auto_approved") and result.get("license_key"):
            session["license_key"] = result["license_key"]  # instant unlock on this device
        return render_template("upgrade.html", submitted=True, req_id=result["id"], checkout_url=checkout_url,
                                auto_approved=result.get("auto_approved", False),
                                grace_hours=result.get("grace_hours"))
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
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin/login.html")
    password = request.form.get("password", "")
    if ADMIN_PASSWORD and password == ADMIN_PASSWORD:
        session["admin_authed"] = True
        next_url = request.args.get("next") or url_for("admin_dashboard")
        return redirect(next_url)
    return render_template("admin/login.html", error="Incorrect password.")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_authed", None)
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    keys = persistence.load_license_keys()
    reqs = persistence.load_requests()
    posts = persistence.load_blogs()
    active_keys = sum(1 for k, v in keys.items() if licensing.is_subscription_active(v) and not v.get("revoked"))
    pending_reqs = sum(1 for r in reqs if r.get("status") in ("pending", "payment_pending"))
    return render_template("admin/dashboard.html",
                            total_keys=len(keys), active_keys=active_keys,
                            pending_reqs=pending_reqs, total_posts=len(posts),
                            github_configured=bool(os.environ.get("GITHUB_TOKEN")))


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
        return redirect(url_for("admin_keys"))
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
    return render_template("admin/blog.html", posts=posts)


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


@app.route("/tools")
def tools_hub():
    return render_template("tools.html", lang_options=audio_tools.LANG_OPTIONS, usage=usage_summary(),
                            filedesk_url=os.environ.get("FILEDESK_URL", "").strip())


@app.route("/api/tools/transcribe", methods=["POST"])
def api_transcribe():
    lim = get_limits()
    if not _check_and_bump("usage_transcribe", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Free daily limit reached ({lim['FREE_DAILY_ACTIONS']}/day). Upgrade to Pro for unlimited."}), 402
    file = request.files.get("file")
    lang_code = request.form.get("lang_code", "en-US")
    if not file:
        return jsonify({"error": "No file uploaded."}), 400
    try:
        result = audio_tools.transcribe(file.read(), file.filename, lang_code)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tools/convert", methods=["POST"])
def api_convert():
    lim = get_limits()
    if not _check_and_bump("usage_convert", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Free daily limit reached ({lim['FREE_DAILY_ACTIONS']}/day). Upgrade to Pro for unlimited."}), 402
    file = request.files.get("file")
    output_format = request.form.get("output_format", "mp3")
    quality = int(request.form.get("quality", 192))
    if not file:
        return jsonify({"error": "No file uploaded."}), 400
    try:
        out_bytes = audio_tools.convert(file.read(), file.filename, output_format, quality)
        return jsonify({"audio_b64": base64.b64encode(out_bytes).decode("ascii"),
                         "filename": f"converted-{int(time.time())}.{output_format}",
                         "format": output_format})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tools/merge", methods=["POST"])
def api_merge():
    lim = get_limits()
    if not _check_and_bump("usage_merge", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Free daily limit reached ({lim['FREE_DAILY_ACTIONS']}/day). Upgrade to Pro for unlimited."}), 402
    files = request.files.getlist("files")
    gap_ms = int(request.form.get("gap_ms", 500))
    output_format = request.form.get("output_format", "mp3")
    if len(files) < 2:
        return jsonify({"error": "Upload at least 2 files to merge."}), 400
    try:
        pairs = [(f.read(), f.filename) for f in files]
        out_bytes = audio_tools.merge(pairs, gap_ms, output_format)
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
    if not _check_and_bump("usage_cutter", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Free daily limit reached ({lim['FREE_DAILY_ACTIONS']}/day). Upgrade to Pro for unlimited."}), 402
    file = request.files.get("file")
    start_sec = float(request.form.get("start_sec", 0))
    end_sec = float(request.form.get("end_sec", 0))
    if not file:
        return jsonify({"error": "No file uploaded."}), 400
    try:
        out_bytes = audio_tools.trim(file.read(), file.filename, start_sec, end_sec)
        return jsonify({"audio_b64": base64.b64encode(out_bytes).decode("ascii"),
                         "filename": f"trimmed-{int(time.time())}.mp3"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tools/cutter/split", methods=["POST"])
def api_cutter_split():
    lim = get_limits()
    if not _check_and_bump("usage_cutter", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Free daily limit reached ({lim['FREE_DAILY_ACTIONS']}/day). Upgrade to Pro for unlimited."}), 402
    file = request.files.get("file")
    split_sec = float(request.form.get("split_sec", 0))
    if not file:
        return jsonify({"error": "No file uploaded."}), 400
    try:
        part1, part2 = audio_tools.split(file.read(), file.filename, split_sec)
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
    if not _check_and_bump("usage_denoise", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Free daily limit reached ({lim['FREE_DAILY_ACTIONS']}/day). Upgrade to Pro for unlimited."}), 402
    file = request.files.get("file")
    strength = float(request.form.get("strength", 0.5))
    if not file:
        return jsonify({"error": "No file uploaded."}), 400
    try:
        out_bytes = audio_tools.denoise(file.read(), file.filename, strength)
        return jsonify({"audio_b64": base64.b64encode(out_bytes).decode("ascii"),
                         "filename": f"denoised-{int(time.time())}.mp3"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tools/voicechange", methods=["POST"])
def api_voicechange():
    lim = get_limits()
    if not _check_and_bump("usage_voicechange", lim["FREE_DAILY_ACTIONS"]):
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
        return jsonify({"audio_b64": base64.b64encode(out_bytes).decode("ascii"),
                         "filename": f"voicechange-{effect}-{int(time.time())}.mp3"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/tools/videoxtract", methods=["POST"])
def api_videoxtract():
    lim = get_limits()
    if not _check_and_bump("usage_videoxtract", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Free daily limit reached ({lim['FREE_DAILY_ACTIONS']}/day). Upgrade to Pro for unlimited."}), 402
    file = request.files.get("file")
    output_format = request.form.get("output_format", "mp3")
    quality = int(request.form.get("quality", 192))
    if not file:
        return jsonify({"error": "No file uploaded."}), 400
    try:
        out_bytes = audio_tools.video_to_audio(file.read(), file.filename, output_format, quality)
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
    if not _check_and_bump("usage_previews", lim["FREE_PREVIEW_LIMIT"]):
        return jsonify({"error": f"Free preview limit reached ({lim['FREE_PREVIEW_LIMIT']}/day). Upgrade to Pro for unlimited previews."}), 402

    text = default_preview_text(language)
    rate_str = f"{speed_pct - 100:+d}%"
    try:
        audio = tts_dispatch(text, voice_id, rate=rate_str, speed_pct=speed_pct)
    except Exception as e:
        return jsonify({"error": f"Preview error: {str(e)}"}), 500

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

    if not _check_and_bump("usage_singles", lim["FREE_DAILY_ACTIONS"]):
        return jsonify({"error": f"Free daily limit reached ({lim['FREE_DAILY_ACTIONS']} generations/day). Upgrade to Pro for unlimited."}), 402

    rate_str = f"{speed_pct - 100:+d}%"
    try:
        audio = tts_dispatch(text, voice_id, rate=rate_str, ssml_mode=ssml_mode, speed_pct=speed_pct)
    except Exception as e:
        return jsonify({"error": f"Error generating audio: {str(e)}"}), 500

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

    if not _check_and_bump("usage_batches", lim["FREE_BATCH_LIMIT"]):
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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
