"""Short-lived result store so a tool request survives a dropped connection.

Problem: on mobile the browser often loses the connection (screen off, tab
backgrounded, network switch) while a long tool request is still running on the
server. The server finishes the work, but the page shows "Network error" and
the user retries -> duplicate work, double usage counters, double TTS billing,
and lock contention.

Fix: the page tags each tool POST with a random X-Request-Key. The server
saves the finished response under that key (on disk, so every gunicorn worker
sees it). If the connection drops, the page polls GET /api/tools/result/<key>
and receives the saved response instead of re-running anything. A retry that
reuses a key never starts a second job.

Files in RESUME_DIR (default /tmp/voxcraft-resume):
  <key>.run   marker: a request with this key is in flight
  <key>.res   first line = JSON meta, remainder = raw response body
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time

RESUME_DIR = os.environ.get("VOXCRAFT_RESUME_DIR", "/tmp/voxcraft-resume")
DONE_TTL_SEC = 20 * 60        # keep finished results this long
INFLIGHT_TTL_SEC = 700        # > gunicorn --timeout 660; older marker = dead job
MAX_BODY_BYTES = 90 * 1024 * 1024
_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
_last_sweep = 0.0


def valid_key(key: str | None) -> bool:
    return bool(key and _KEY_RE.match(key))


def owner_id(session_token: str | None) -> str:
    """Bind a result to the browser session that started it."""
    return hashlib.sha256((session_token or "anon").encode()).hexdigest()[:20]


def _ensure_dir() -> None:
    os.makedirs(RESUME_DIR, mode=0o700, exist_ok=True)


def _run_path(key: str) -> str:
    return os.path.join(RESUME_DIR, key + ".run")


def _res_path(key: str) -> str:
    return os.path.join(RESUME_DIR, key + ".res")


def _age(path: str) -> float:
    try:
        return time.time() - os.path.getmtime(path)
    except OSError:
        return 1e9


def sweep() -> None:
    """Delete expired files (throttled to once a minute per process)."""
    global _last_sweep
    now = time.time()
    if now - _last_sweep < 60:
        return
    _last_sweep = now
    try:
        for name in os.listdir(RESUME_DIR):
            path = os.path.join(RESUME_DIR, name)
            ttl = INFLIGHT_TTL_SEC if name.endswith(".run") else DONE_TTL_SEC
            if name.endswith(".tmp"):
                ttl = 120
            if _age(path) > ttl:
                try:
                    os.unlink(path)
                except OSError:
                    pass
    except OSError:
        pass


def read_done(key: str, owner: str):
    """Return (status, content_type, body) if a finished result exists for this
    owner, "forbidden" if the key belongs to someone else, or None."""
    path = _res_path(key)
    if _age(path) > DONE_TTL_SEC:
        return None
    try:
        with open(path, "rb") as f:
            meta = json.loads(f.readline().decode("utf-8"))
            body = f.read()
    except (OSError, ValueError):
        return None
    if meta.get("owner") != owner:
        return "forbidden"
    return int(meta.get("status", 200)), meta.get("ctype") or "application/json", body


def claim(key: str, owner: str):
    """Called when a tagged request arrives.

    Returns "claimed" (go ahead and run it), "pending" (same key already
    running), "forbidden", or a (status, content_type, body) tuple (already
    finished -> replay it instead of running again)."""
    try:
        _ensure_dir()
        sweep()
        done = read_done(key, owner)
        if done is not None:
            return done
        for _ in range(2):
            try:
                fd = os.open(_run_path(key), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                if _age(_run_path(key)) > INFLIGHT_TTL_SEC:
                    try:
                        os.unlink(_run_path(key))
                    except OSError:
                        pass
                    continue
                return "pending"
            with os.fdopen(fd, "w") as f:
                json.dump({"owner": owner, "ts": time.time()}, f)
            return "claimed"
        return "pending"
    except OSError:
        # Never block a tool because the cache dir is unavailable.
        return "claimed"


def store(key: str, owner: str, status: int, content_type: str, body: bytes) -> None:
    if len(body) > MAX_BODY_BYTES:
        release(key)
        return
    try:
        _ensure_dir()
        meta = json.dumps({"owner": owner, "status": int(status), "ctype": content_type, "ts": time.time()})
        tmp = _res_path(key) + ".tmp"
        with open(tmp, "wb") as f:
            f.write(meta.encode("utf-8") + b"\n")
            f.write(body)
        os.replace(tmp, _res_path(key))
    except OSError:
        pass
    finally:
        release(key)


def release(key: str) -> None:
    try:
        os.unlink(_run_path(key))
    except OSError:
        pass


def lookup(key: str, owner: str):
    """For the polling endpoint: (status, ctype, body) | "pending" | "forbidden" | None."""
    done = read_done(key, owner)
    if done is not None:
        return done
    run = _run_path(key)
    if os.path.exists(run) and _age(run) <= INFLIGHT_TTL_SEC:
        return "pending"
    return None
