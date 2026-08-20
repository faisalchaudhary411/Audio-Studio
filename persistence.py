"""
persistence.py — SQLite-backed storage, replacing the GitHub-JSON approach.

Why this replaced the GitHub API version: that design existed because
Render's filesystem isn't persistent (wiped on every redeploy), so local
disk wasn't an option there. On the InterServer VPS, disk IS persistent, so
a local SQLite file is simpler, faster (no network round-trip per read/
write), has no GitHub API rate limits, and — the main motivation — supports
real atomic transactions. The old load-whole-dict/mutate/save-whole-dict
pattern had a genuine race condition: two people activating the same
not-yet-used license key at nearly the same instant could both read
"unused" before either write landed, and both succeed. `license_key_
transaction()` below closes that window with a real SQLite transaction.

PUBLIC API IS UNCHANGED from the GitHub-JSON version — every load_*/save_*
function has the same name and signature as before, so app.py,
pro_requests.py, and usage_tracking.py needed zero changes. Only
licensing.py's activate_vox_license was updated, to use the new atomic
license_key_transaction() instead of load-then-save.

IMPORTANT — migrating existing data: if you have real customer data in the
old GitHub-JSON files (license keys people already paid for!), run
deploy/migrate_to_sqlite.py ONCE before switching the app over to this file,
or those customers' Pro status will appear to vanish. See that script's
docstring and the deploy README.
"""

import os
import json
import sqlite3
import contextlib
import threading
import random

DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "voxcraft.db"),
)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Serializes writer transactions from *within this process* so concurrent
# gunicorn threads don't collide before even reaching SQLite's own locking.
# SQLite's own file-level locking (BEGIN IMMEDIATE) handles cross-process
# safety across gunicorn's 2 worker processes; this lock just avoids
# needless "database is locked" retries between threads of the SAME worker.
_write_lock = threading.Lock()

DEFAULT_LIMITS = {
    "FREE_CHAR_LIMIT": 5000,
    "FREE_MONTHLY_CHAR_QUOTA": 50000,
    "FREE_DAILY_ACTIONS": 10,
    "FREE_BATCH_LIMIT": 5,
    "FREE_BATCH_MAX_LINES": 20,
    "FREE_PREVIEW_LIMIT": 5,
    "PRO_BATCH_MAX": 20,
    "FREE_VOICES_COUNT": 20,
    "PRO_PRICE_PKR": 840,
    "PRO_PRICE_LABEL": "840 PKR",
    "PRO_PRICE_USD_LABEL": "$3",
    # Pro+ previously had NO PKR fields at all — only Pro did — so the
    # manual-payment flow (EasyPaisa/JazzCash/bank, used by Pakistani
    # customers who can't pay by card) never told a Pro+ buyer how many
    # rupees to actually send. Mirrors the existing Pro fields exactly.
    "PRO_PLUS_PRICE_PKR": 1680,
    "PRO_PLUS_PRICE_LABEL": "1680 PKR",
    "PRO_PLUS_PRICE_USD_LABEL": "$6",
    "FREE_PRICE_LABEL": "$0",
    "CHECKOUT_URL": "",
    # Was one field for both plans, so every checkout — Pro or Pro+ — sent
    # the person to the same Freemius checkout link, which is why Pro+
    # buyers landed on the Pro plan page: the button never varied by which
    # plan they'd picked, because there was only ever one URL to point it
    # at. See templates/upgrade.html for the plan-aware fix.
    "CHECKOUT_URL_PRO_PLUS": "",
    "FREE_FEATURES": "",
    "PRO_FEATURES": "",
    "AUTO_APPROVE_MANUAL": True,
    "MANUAL_GRACE_HOURS": 72,
}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    # WAL: readers don't block writers and vice versa — matters once the
    # webhook auto-deploy listener and the main app are both touching the
    # DB (they're separate processes). busy_timeout: if two writers do
    # collide, retry for up to 5s instead of failing immediately.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    """Creates tables if they don't exist. Called once at import time below
    — safe to call repeatedly (CREATE TABLE IF NOT EXISTS)."""
    with _write_lock:
        conn = _connect()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS license_keys (
                    key  TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS blogs (
                    id       TEXT PRIMARY KEY,
                    position INTEGER NOT NULL,
                    data     TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS requests (
                    id       TEXT PRIMARY KEY,
                    position INTEGER NOT NULL,
                    data     TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS limits (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS usage (
                    ip_hash TEXT PRIMARY KEY,
                    data    TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS login_attempts (
                    ip_hash TEXT PRIMARY KEY,
                    data    TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS announcements (
                    id       TEXT PRIMARY KEY,
                    position INTEGER NOT NULL,
                    data     TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS traffic_hits (
                    date    TEXT NOT NULL,
                    ip_hash TEXT NOT NULL,
                    hits    INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (date, ip_hash)
                );
            """)
            conn.commit()
        finally:
            conn.close()


init_db()


def _replace_ordered_table(table: str, id_field: str, items: list) -> tuple:
    """Shared logic for blogs/requests: both are 'save the whole list, in
    the order given' semantics, same as the old gh_write(whole JSON list).
    Replaces all rows in one transaction so a reader never sees a
    half-replaced table."""
    try:
        with _write_lock:
            conn = _connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(f"DELETE FROM {table}")
                for position, item in enumerate(items):
                    item_id = str(item.get(id_field, position))
                    conn.execute(
                        f"INSERT INTO {table}(id, position, data) VALUES (?, ?, ?)",
                        (item_id, position, json.dumps(item, ensure_ascii=False)),
                    )
                conn.commit()
                return True, ""
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
    except Exception as e:
        return False, str(e)


def _load_ordered_table(table: str) -> list:
    conn = _connect()
    try:
        rows = conn.execute(f"SELECT data FROM {table} ORDER BY position ASC").fetchall()
        return [json.loads(r[0]) for r in rows]
    finally:
        conn.close()


# ---- blogs ----
def load_blogs() -> list:
    return _load_ordered_table("blogs")


def save_blogs(posts: list) -> tuple:
    return _replace_ordered_table("blogs", "id", posts)


# ---- announcements (admin-authored notices — discounts / product updates —
#      shown to visitors via the bell dropdown + optional top banner) ----
def load_announcements() -> list:
    return _load_ordered_table("announcements")


def save_announcements(items: list) -> tuple:
    return _replace_ordered_table("announcements", "id", items)


def load_active_announcements(limit: int = 20) -> list:
    """Newest-first, only items that are active and not past their expiry
    date. Filtering happens here (not client-side) so an expired discount
    can never leak into the API response even briefly."""
    import datetime as _dt
    today = _dt.date.today().isoformat()
    items = load_announcements()
    live = [
        a for a in items
        if a.get("active") and (not a.get("expires") or a.get("expires") >= today)
    ]
    live.sort(key=lambda a: a.get("created", ""), reverse=True)
    return live[:limit]


# ---- traffic (lightweight daily visitor/pageview counter — NOT the same
#      table as `usage` above, which tracks free-tier quota consumption and
#      keeps a full JSON blob per IP/fingerprint. This one is a single-row
#      upsert per (date, ip_hash) so logging a pageview never requires
#      loading the whole table, unlike the load-dict/mutate/save-dict
#      pattern used elsewhere — that would get slower every single day as
#      history accumulates, which is untenable for something written on
#      nearly every request.) ----
def log_visit(ip_hash: str, date: str = None):
    """Increments today's hit count for this IP hash — one row per
    (date, ip_hash), so COUNT(DISTINCT ip_hash) for a date is 'unique
    visitors' and SUM(hits) is 'pageviews'. 1-in-500 calls also prunes rows
    older than 180 days, keeping the table from growing forever without
    needing a separate cron job — cheap enough to piggyback on a request
    that's already writing here."""
    import datetime as _dt
    date = date or _dt.date.today().isoformat()
    with _write_lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO traffic_hits(date, ip_hash, hits) VALUES (?, ?, 1) "
                "ON CONFLICT(date, ip_hash) DO UPDATE SET hits = hits + 1",
                (date, ip_hash),
            )
            if random.random() < 0.002:
                cutoff = (_dt.date.today() - _dt.timedelta(days=180)).isoformat()
                conn.execute("DELETE FROM traffic_hits WHERE date < ?", (cutoff,))
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            conn.close()


def get_daily_traffic(days: int = 30) -> list:
    """Newest-first list of {date, visitors, pageviews} for the last `days`
    calendar days (including days with zero traffic, so a chart doesn't
    silently skip gaps)."""
    import datetime as _dt
    today = _dt.date.today()
    start = (today - _dt.timedelta(days=days - 1)).isoformat()
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT date, COUNT(DISTINCT ip_hash) AS visitors, SUM(hits) AS pageviews "
            "FROM traffic_hits WHERE date >= ? GROUP BY date",
            (start,),
        ).fetchall()
    finally:
        conn.close()
    by_date = {r[0]: {"visitors": r[1], "pageviews": r[2]} for r in rows}
    out = []
    for i in range(days):
        d = (today - _dt.timedelta(days=i)).isoformat()
        stats = by_date.get(d, {"visitors": 0, "pageviews": 0})
        out.append({"date": d, "visitors": stats["visitors"], "pageviews": stats["pageviews"]})
    return out


# ---- requests ----
def load_requests() -> list:
    return _load_ordered_table("requests")


def save_requests(reqs: list) -> tuple:
    return _replace_ordered_table("requests", "id", reqs)


# ---- limits (key/value, not JSON-list-shaped like the above two) ----
def load_limits() -> dict:
    conn = _connect()
    try:
        rows = conn.execute("SELECT key, value FROM limits").fetchall()
        stored = {k: json.loads(v) for k, v in rows}
    finally:
        conn.close()
    merged = DEFAULT_LIMITS.copy()
    merged.update({k: stored[k] for k in stored if k in DEFAULT_LIMITS})
    return merged


def save_limits(limits: dict) -> tuple:
    try:
        with _write_lock:
            conn = _connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("DELETE FROM limits")
                for k, v in limits.items():
                    conn.execute(
                        "INSERT INTO limits(key, value) VALUES (?, ?)",
                        (k, json.dumps(v, ensure_ascii=False)),
                    )
                conn.commit()
                return True, ""
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
    except Exception as e:
        return False, str(e)


# ---- license keys (whole-dict load/save, for admin bulk ops — the
#      activation hot path uses license_key_transaction() below instead) ----
def load_license_keys() -> dict:
    conn = _connect()
    try:
        rows = conn.execute("SELECT key, data FROM license_keys").fetchall()
        return {k: json.loads(v) for k, v in rows}
    finally:
        conn.close()


def save_license_keys(keys: dict) -> tuple:
    try:
        with _write_lock:
            conn = _connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("DELETE FROM license_keys")
                for k, v in keys.items():
                    conn.execute(
                        "INSERT INTO license_keys(key, data) VALUES (?, ?)",
                        (k, json.dumps(v, ensure_ascii=False)),
                    )
                conn.commit()
                return True, ""
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
    except Exception as e:
        return False, str(e)


@contextlib.contextmanager
def license_key_transaction(key: str):
    """Atomic read-modify-write for ONE license key — this is what actually
    closes the activation race condition. BEGIN IMMEDIATE grabs SQLite's
    write lock at the very start of the transaction (not lazily on first
    write), so if two requests hit this for the SAME key at nearly the same
    instant, the second one blocks until the first fully commits, then sees
    the now-updated state (e.g. "used": True) instead of racing against it.

    Usage:
        with persistence.license_key_transaction(key) as holder:
            info = holder["info"]          # dict, or None if key doesn't exist
            if info is None:
                return {"valid": False, "error": "Invalid key."}
            ...mutate info in place, or reassign holder["info"] = info...
            # whatever holder["info"] is when the `with` block exits gets
            # written back automatically (unless you set it to None).
    """
    with _write_lock:
        conn = _connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT data FROM license_keys WHERE key = ?", (key,)).fetchone()
            holder = {"info": json.loads(row[0]) if row else None}
            yield holder
            if holder["info"] is not None:
                conn.execute(
                    "INSERT INTO license_keys(key, data) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET data = excluded.data",
                    (key, json.dumps(holder["info"], ensure_ascii=False)),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


# ---- usage tracking (dict keyed by ip_hash) ----
def load_usage() -> dict:
    """Whole-table read. Only used by migrate_to_sqlite.py's one-time
    import — NOT used for live enforcement anymore, see
    usage_pair_transaction() below for why."""
    conn = _connect()
    try:
        rows = conn.execute("SELECT ip_hash, data FROM usage").fetchall()
        return {k: json.loads(v) for k, v in rows}
    finally:
        conn.close()


def save_usage(data: dict) -> tuple:
    """Whole-table replace. Only used by migrate_to_sqlite.py's one-time
    import — NEVER call this from live request handling. Wiping and
    reinserting the entire table from one process's snapshot is exactly
    the pattern that caused the cross-worker data-loss bug described in
    usage_pair_transaction()'s docstring; that function replaced every
    live call site of this one."""
    try:
        with _write_lock:
            conn = _connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("DELETE FROM usage")
                for k, v in data.items():
                    conn.execute(
                        "INSERT INTO usage(ip_hash, data) VALUES (?, ?)",
                        (k, json.dumps(v, ensure_ascii=False)),
                    )
                conn.commit()
                return True, ""
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
    except Exception as e:
        return False, str(e)


@contextlib.contextmanager
def usage_pair_transaction(key_a: str, key_b: str):
    """Atomic read-modify-write across the two per-visitor usage rows
    (IP-hash-keyed and browser-fingerprint-keyed) that usage_tracking.py
    maintains for every free-tier counter.

    BUG THIS REPLACES: usage_tracking.py used to keep ONE big dict in
    process memory as its real source of truth — loaded once per gunicorn
    worker via load_usage(), mutated in memory on every check/bump, and
    periodically flushed back with save_usage() (a full DELETE + reinsert
    of the ENTIRE table from that worker's in-memory copy).

    With `--workers 2` (see deploy/voxcraft.service), that's two separate
    OS processes, each with its own independent copy of that dict — Python
    globals aren't shared across a fork after --preload hands off to the
    workers. Two concrete failures followed from that:

    1. Under-enforcement: a free user's requests land on worker A and
       worker B roughly alternately under normal load. Each worker only
       ever saw (and enforced against) the increments IT had personally
       processed, since it never re-read the other worker's writes from
       disk after its own first load. A visitor with 10 requests split
       ~5/5 across both workers could pass a "10 generations/day" check on
       BOTH workers, using up to ~2x the configured limit before either
       worker's own counter reached it.
    2. Data loss: save_usage()'s DELETE-then-reinsert-everything pattern
       means whichever worker's background flush thread runs LAST wins —
       it overwrites the whole table with only what's in ITS memory,
       silently erasing increments a different worker wrote for a
       DIFFERENT visitor in the meantime (that visitor's counts could
       appear to reset with no user action, or a batch run that should
       have been blocked wasn't, because the block that had just been
       recorded got wiped by the other worker's stale snapshot).

    Fixed the same way license_key_transaction() (above) already fixes
    the equivalent race for license key activation: BEGIN IMMEDIATE grabs
    SQLite's write lock up front, so the read, the caller's mutation, and
    the write all happen inside ONE transaction, on ONE row at a time —
    correctness now comes from SQLite's own cross-process file locking,
    not from an in-process cache that can't see what a sibling process is
    doing.

    Usage:
        with persistence.usage_pair_transaction(ip_key, fp_key) as holder:
            # holder["a"] / holder["b"]: current record for each key, or
            # None if that key has no row yet.
            merged = ...compute effective record from holder["a"]/["b"]...
            merged = ...apply the read or the increment...
            holder["record"] = merged   # written back to BOTH keys on exit
            # leave holder["record"] as None for a read-only check — nothing
            # gets written if you don't set it.
    """
    with _write_lock:
        conn = _connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row_a = conn.execute("SELECT data FROM usage WHERE ip_hash = ?", (key_a,)).fetchone()
            row_b = conn.execute("SELECT data FROM usage WHERE ip_hash = ?", (key_b,)).fetchone()
            holder = {
                "a": json.loads(row_a[0]) if row_a else None,
                "b": json.loads(row_b[0]) if row_b else None,
                "record": None,
            }
            yield holder
            if holder["record"] is not None:
                payload = json.dumps(holder["record"], ensure_ascii=False)
                for k in (key_a, key_b):
                    conn.execute(
                        "INSERT INTO usage(ip_hash, data) VALUES (?, ?) "
                        "ON CONFLICT(ip_hash) DO UPDATE SET data = excluded.data",
                        (k, payload),
                    )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


# ---- admin login attempt tracking (brute-force lockout) ----
# Deliberately a separate small table rather than reusing the `usage` table
# — different access pattern (single-row get/set per IP, not a whole-table
# load/save), and mixing concerns there would make both harder to reason
# about. Stored in the DB rather than an in-memory dict specifically
# because gunicorn runs multiple worker processes (see voxcraft.service) —
# an in-memory counter would only apply per-worker, silently doubling (or
# more) the effective attempt budget an attacker gets.
def get_login_attempts(ip_hash: str) -> dict:
    conn = _connect()
    try:
        row = conn.execute("SELECT data FROM login_attempts WHERE ip_hash = ?", (ip_hash,)).fetchone()
        return json.loads(row[0]) if row else {}
    finally:
        conn.close()


def set_login_attempts(ip_hash: str, record: dict):
    with _write_lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO login_attempts(ip_hash, data) VALUES (?, ?) "
                "ON CONFLICT(ip_hash) DO UPDATE SET data = excluded.data",
                (ip_hash, json.dumps(record, ensure_ascii=False)),
            )
            conn.commit()
        finally:
            conn.close()


def clear_login_attempts(ip_hash: str):
    with _write_lock:
        conn = _connect()
        try:
            conn.execute("DELETE FROM login_attempts WHERE ip_hash = ?", (ip_hash,))
            conn.commit()
        finally:
            conn.close()
