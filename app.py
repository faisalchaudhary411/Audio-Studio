"""
VoxCraft — Flask app, TTS tool ported for real (edge-tts + gTTS fallback,
markup mode, single + batch generation).

Everything else (Transcribe, Convert, Merge, Cutter, Music, Denoise,
VoiceChanger, VideoExtract, admin, payments, ads, blog) is NOT ported yet —
this pass is TTS only, on purpose, per your instruction.

TODO before this replaces the Streamlit app:
- Real Pro / license-key check (is_pro() below is a session-cookie stub —
  original app used IP-based usage tracking synced via your GitHub backend,
  which this does not replicate yet).
- ElevenLabs cloned-voice routing (EL:: prefix) — stripped out for this pass.
- Google-engine voices (GT:: prefix, the "More Languages" category) — stripped
  out for this pass; those route through gTTS directly rather than edge-tts.
- The other 8 tools, admin panel, payments, ads, blog.
"""

from flask import Flask, render_template, request, jsonify, session, send_file
import os
import io
import time
import zipfile
import base64
import datetime as dt

from voices import VOICES, FREE_VOICES, default_preview_text
from tts_engine import tts_dispatch
from clone_engine import start_clone_job, get_job
from werkzeug.utils import secure_filename

CLONE_UPLOAD_DIR = "/tmp/voxcraft_clone_refs"
os.makedirs(CLONE_UPLOAD_DIR, exist_ok=True)
CLONE_CHAR_LIMIT = 500  # tighter than normal TTS — keeps CPU generation time bounded

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

FREE_CHAR_LIMIT = 5000        # per "month" — see is_pro/session TODO above
FREE_DAILY_ACTIONS = 10       # single generations/day
FREE_BATCH_LIMIT = 5          # batch generations/day
FREE_PREVIEW_LIMIT = 5        # previews/day
BATCH_MAX_LINES = 20


def is_pro() -> bool:
    """TODO: replace with real license-key check against Freemius."""
    return session.get("is_pro", False)


def _today() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d")


def _reset_daily_if_needed():
    if session.get("usage_date") != _today():
        session["usage_date"] = _today()
        session["usage_singles"] = 0
        session["usage_batches"] = 0
        session["usage_previews"] = 0
        session["usage_chars"] = 0


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


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/studio")
def studio():
    active_voices = VOICES if is_pro() else FREE_VOICES
    return render_template("studio.html", voices=active_voices, pro=is_pro(),
                            free_char_limit=FREE_CHAR_LIMIT, batch_max=BATCH_MAX_LINES)


@app.route("/pricing")
def pricing():
    return render_template("pricing.html")


@app.route("/api/tts/preview", methods=["POST"])
def api_preview():
    data = request.get_json(force=True) or {}
    language = data.get("language", "US English")
    voice_id = data.get("voice_id")
    speed_pct = int(data.get("speed_pct", 100))

    if not voice_id:
        return jsonify({"error": "No voice selected."}), 400

    if not _check_and_bump("usage_previews", FREE_PREVIEW_LIMIT):
        return jsonify({"error": f"Free preview limit reached ({FREE_PREVIEW_LIMIT}/day). Upgrade to Pro for unlimited previews."}), 402

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

    char_limit_widget = None if is_pro() else FREE_CHAR_LIMIT
    if char_limit_widget and len(text) > char_limit_widget:
        return jsonify({"error": f"Free plan is capped at {char_limit_widget:,} characters. Upgrade to Pro for unlimited length."}), 402

    if not _check_and_bump("usage_singles", FREE_DAILY_ACTIONS):
        return jsonify({"error": f"Free daily limit reached ({FREE_DAILY_ACTIONS} generations/day). Upgrade to Pro for unlimited."}), 402

    rate_str = f"{speed_pct - 100:+d}%"
    try:
        audio = tts_dispatch(text, voice_id, rate=rate_str, ssml_mode=ssml_mode, speed_pct=speed_pct)
    except Exception as e:
        return jsonify({"error": f"Error generating audio: {str(e)}"}), 500

    if not is_pro():
        _reset_daily_if_needed()
        session["usage_chars"] = session.get("usage_chars", 0) + len(text)

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

    max_lines = BATCH_MAX_LINES if not is_pro() else 999
    if len(lines) > max_lines:
        return jsonify({"error": f"{'Pro' if is_pro() else 'Free'} plan limit is {max_lines} lines."}), 402

    if not _check_and_bump("usage_batches", FREE_BATCH_LIMIT):
        return jsonify({"error": f"Free batch limit reached ({FREE_BATCH_LIMIT}/day). Upgrade to Pro for unlimited."}), 402

    rate_str = f"{speed_pct - 100:+d}%"
    results = []
    errors = []
    timestamp_base = int(time.time())

    for idx, line in enumerate(lines):
        try:
            audio = tts_dispatch(line, voice_id, rate=rate_str, speed_pct=speed_pct)
            fname = f"tts-batch-{idx + 1:02d}-{timestamp_base}.mp3"
            results.append({"idx": idx + 1, "text": line, "filename": fname, "audio": audio})
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
