import base64
import uuid
import datetime as dt

import persistence
import pro_requests


def _unique_txn_id():
    return f"txn{uuid.uuid4().hex[:12]}"


def _fake_request(ip_hash="test-ip-hash", status="approved", txn_id="", screenshot_hash=""):
    """A minimal request record — matches what submit_pro_request would
    have written, for the duplicate-checker functions which only read
    persistence.load_requests(), not the submit function itself. Uses
    'now' for the date so it falls inside the rate-limiter's 24h window —
    a fixed past date would make rate-limit tests silently pass for the
    wrong reason (the record being skipped as too old, not counted)."""
    return {
        "id": f"REQ-{uuid.uuid4().hex[:10]}", "status": status,
        "txn_id": txn_id, "screenshot_sha256": screenshot_hash,
        "ip": ip_hash, "date": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def test_txn_id_duplicate_detected_across_live_requests():
    txn = _unique_txn_id()
    reqs = persistence.load_requests()
    reqs.insert(0, _fake_request(status="approved", txn_id=txn))
    persistence.save_requests(reqs)

    assert pro_requests._txn_id_is_duplicate(txn) is True


def test_txn_id_not_duplicate_when_only_seen_on_rejected_request():
    """A rejected request's txn_id must be resubmittable — rejection often
    means 'fix and try again', not 'this evidence is permanently burned'."""
    txn = _unique_txn_id()
    reqs = persistence.load_requests()
    reqs.insert(0, _fake_request(status="rejected", txn_id=txn))
    persistence.save_requests(reqs)

    assert pro_requests._txn_id_is_duplicate(txn) is False


def test_txn_id_duplicate_excludes_self():
    """When checking a request being re-evaluated, it shouldn't flag
    itself as a duplicate of its own txn_id."""
    txn = _unique_txn_id()
    reqs = persistence.load_requests()
    record = _fake_request(status="pending", txn_id=txn)
    reqs.insert(0, record)
    persistence.save_requests(reqs)

    assert pro_requests._txn_id_is_duplicate(txn, exclude_req_id=record["id"]) is False


def test_empty_txn_id_never_flagged_as_duplicate():
    assert pro_requests._txn_id_is_duplicate("") is False


def test_screenshot_duplicate_detected_by_exact_hash():
    raw = b"fake image bytes for testing"
    b64 = base64.b64encode(raw).decode()
    digest = pro_requests._screenshot_sha256(b64)

    reqs = persistence.load_requests()
    reqs.insert(0, _fake_request(status="approved", screenshot_hash=digest))
    persistence.save_requests(reqs)

    assert pro_requests._screenshot_is_duplicate(digest) is True


def test_different_screenshots_never_flagged_as_duplicate():
    hash_a = pro_requests._screenshot_sha256(base64.b64encode(b"image A").decode())
    hash_b = pro_requests._screenshot_sha256(base64.b64encode(b"image B").decode())
    reqs = persistence.load_requests()
    reqs.insert(0, _fake_request(status="approved", screenshot_hash=hash_a))
    persistence.save_requests(reqs)

    assert pro_requests._screenshot_is_duplicate(hash_b) is False


def test_ocr_extract_text_returns_empty_for_garbage_input():
    """Covers the 'tesseract not installed' and 'not a real image' cases
    identically — both must degrade to '', never raise."""
    assert pro_requests._ocr_extract_text("") == ""
    assert pro_requests._ocr_extract_text("not-valid-base64-at-all!!!") == ""


def test_ocr_txn_id_found_matches_digits_ignoring_punctuation():
    assert pro_requests._ocr_txn_id_found("ref no: 123-456-789", "123456789") is True


def test_ocr_txn_id_found_false_when_absent():
    assert pro_requests._ocr_txn_id_found("totally unrelated text", "123456789") is False


def test_ocr_txn_id_too_short_never_matches():
    """Guards against false positives: a 2-3 digit txn_id would trivially
    appear somewhere in any receipt image by coincidence."""
    assert pro_requests._ocr_txn_id_found("call 123 for help", "123") is False


def test_ocr_amount_found_exact_token_match():
    assert pro_requests._ocr_amount_found("total paid: rs 840 thank you", 840) is True


def test_ocr_amount_found_does_not_substring_match():
    """840 must not match inside 8400 — that's the whole reason this uses
    exact token comparison instead of the digits-only substring check
    used for txn_id."""
    assert pro_requests._ocr_amount_found("total paid: rs 8400", 840) is False


def test_rate_limited_blocks_after_threshold():
    ip_hash = f"rate-test-{uuid.uuid4().hex[:8]}"
    reqs = persistence.load_requests()
    for _ in range(pro_requests.RATE_LIMIT_MAX_PENDING_PER_IP):
        reqs.insert(0, _fake_request(ip_hash=ip_hash, status="pending"))
    persistence.save_requests(reqs)

    assert pro_requests._rate_limited(ip_hash) is True


def test_rate_limited_false_under_threshold():
    ip_hash = f"rate-test-{uuid.uuid4().hex[:8]}"
    assert pro_requests._rate_limited(ip_hash) is False
