import uuid

import api_keys


def _unique_email():
    return f"test-{uuid.uuid4().hex[:10]}@example.com"


def test_create_api_key_hash_matches_raw_key():
    result = api_keys.create_api_key("Test User", _unique_email(), "api_starter", 200000)
    assert api_keys.hash_key(result["raw_key"]) == result["record"]["key_hash"]
    assert result["record"]["active"] is True
    assert result["record"]["monthly_char_quota"] == 200000


def test_find_key_by_email_dedup_respects_plan_filter():
    email = _unique_email()
    api_keys.create_api_key("Test User", email, "api_free", 10000)
    found_free = api_keys.find_key_by_email(email, plan="api_free")
    found_starter = api_keys.find_key_by_email(email, plan="api_starter")
    assert found_free is not None
    assert found_starter is None  # no api_starter key exists for this email


def test_find_keys_by_email_returns_all_matches():
    email = _unique_email()
    api_keys.create_api_key("Test User", email, "api_free", 10000)
    api_keys.create_api_key("Test User", email, "api_pro", 1000000)
    matches = api_keys.find_keys_by_email(email)
    assert len(matches) == 2
    assert {m["plan"] for m in matches} == {"api_free", "api_pro"}


def test_rotate_key_revokes_old_and_creates_new_with_same_terms():
    email = _unique_email()
    original = api_keys.create_api_key("Test User", email, "api_starter", 200000)
    old_id = original["record"]["id"]

    rotated = api_keys.rotate_key(old_id)

    assert rotated  # non-empty dict
    assert rotated["record"]["customer_email"] == email
    assert rotated["record"]["plan"] == "api_starter"
    assert rotated["record"]["monthly_char_quota"] == 200000
    assert rotated["raw_key"] != original["raw_key"]

    # old key should now be revoked, not deleted
    old_record = next(k for k in api_keys.find_keys_by_email(email) if k["id"] == old_id)
    assert old_record["active"] is False


def test_rotate_key_unknown_id_returns_empty_dict():
    assert api_keys.rotate_key("nonexistent-id-12345") == {}


def test_sync_key_from_freemius_event_cancelled_revokes():
    email = _unique_email()
    fs_id = f"fs-{uuid.uuid4().hex[:12]}"
    result = api_keys.create_api_key("Test User", email, "api_pro", 1000000, freemius_license_id=fs_id)

    sync_result = api_keys.sync_key_from_freemius_event(fs_id, "license.cancelled")
    assert sync_result["success"] is True
    assert sync_result["action"] == "revoked"

    record = next(k for k in api_keys.find_keys_by_email(email) if k["id"] == result["record"]["id"])
    assert record["active"] is False


def test_sync_key_from_freemius_event_extended_unrevokes():
    email = _unique_email()
    fs_id = f"fs-{uuid.uuid4().hex[:12]}"
    result = api_keys.create_api_key("Test User", email, "api_pro", 1000000, freemius_license_id=fs_id)
    api_keys.revoke_key(result["record"]["id"])

    sync_result = api_keys.sync_key_from_freemius_event(fs_id, "license.extended")
    assert sync_result["success"] is True
    assert sync_result["action"] == "unrevoked"

    record = next(k for k in api_keys.find_keys_by_email(email) if k["id"] == result["record"]["id"])
    assert record["active"] is True


def test_sync_key_from_freemius_event_unknown_id_is_noop_not_error():
    """This is the browser-Pro-license case: the same webhook fires for
    both product lines, so most events won't correspond to any API key at
    all — that must be a quiet no-op, not something that looks like a
    failure in logs."""
    result = api_keys.sync_key_from_freemius_event("no-such-freemius-id", "license.cancelled")
    assert result["success"] is False
    assert result["reason"] == "not_an_api_key"


# ---------------------------------------------------------------------------
# Wholesale / bulk-key features
# ---------------------------------------------------------------------------
import threading


def _wholesale(**kw):
    return api_keys.create_api_key("Reseller", _unique_email(), "api_wholesale", 5_000_000, **kw)


def test_old_style_key_has_safe_wholesale_defaults():
    rec = api_keys.create_api_key("Test", _unique_email(), "api_starter", 200000)["record"]
    assert rec["billing_mode"] == "monthly"
    assert rec["rpm_limit"] == 0
    assert rec["allowed_voices"] == []
    assert api_keys.voice_allowed(rec, "any-voice")
    assert api_keys.effective_max_chars(rec, 5000) == 5000


def test_limits_are_clamped_and_voices_normalised():
    rec = _wholesale(rpm_limit=-5, max_chars_per_request=999999,
                     allowed_voices="ur-PK-UzmaNeural, ur-PK-AsadNeural\nur-PK-UzmaNeural")["record"]
    assert rec["rpm_limit"] == 0
    assert rec["max_chars_per_request"] == api_keys.MAX_CHARS_PER_REQUEST_CEILING
    assert rec["allowed_voices"] == ["ur-PK-UzmaNeural", "ur-PK-AsadNeural"]
    assert api_keys.voice_allowed(rec, "ur-PK-UzmaNeural")
    assert not api_keys.voice_allowed(rec, "en-US-AvaNeural")


def test_prepaid_balance_topup_deduct_and_never_negative():
    rec = _wholesale(billing_mode="prepaid")["record"]
    h = rec["key_hash"]
    assert api_keys.would_exceed_quota(rec, 1)  # empty balance
    assert api_keys.top_up_balance(h, 1000) == 1000
    assert not api_keys.would_exceed_quota(rec, 1000)
    assert api_keys.would_exceed_quota(rec, 1001)
    api_keys.bump_usage(h, 400, prepaid=True)
    assert api_keys.get_usage(h)["balance"] == 600
    api_keys.bump_usage(h, 5000, prepaid=True)  # overshoot window
    assert api_keys.get_usage(h)["balance"] == 0
    with __import__("pytest").raises(ValueError):
        api_keys.top_up_balance(h, 0)


def test_monthly_key_unaffected_by_balance_logic():
    rec = api_keys.create_api_key("T", _unique_email(), "api_starter", 100)["record"]
    api_keys.bump_usage(rec["key_hash"], 60)
    assert api_keys.remaining_chars(rec) == 40
    assert not api_keys.would_exceed_quota(rec, 40)
    assert api_keys.would_exceed_quota(rec, 41)


def test_rate_limit_blocks_after_limit_and_unlimited_when_zero():
    rec = _wholesale(rpm_limit=3)["record"]
    results = [api_keys.check_rate_limit(rec)[0] for _ in range(5)]
    assert results == [True, True, True, False, False]
    allowed, retry, _ = api_keys.check_rate_limit(rec)
    assert not allowed and 1 <= retry <= 60

    unlimited = _wholesale()["record"]
    assert all(api_keys.check_rate_limit(unlimited)[0] for _ in range(50))


def test_rate_limit_is_atomic_under_concurrency():
    rec = _wholesale(rpm_limit=10)["record"]
    allowed = []
    lock = threading.Lock()

    def hit():
        ok = api_keys.check_rate_limit(rec)[0]
        with lock:
            allowed.append(ok)

    threads = [threading.Thread(target=hit) for _ in range(30)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sum(allowed) == 10


def test_usage_report_daily_history_and_modes():
    rec = _wholesale(billing_mode="prepaid")["record"]
    h = rec["key_hash"]
    api_keys.top_up_balance(h, 10000)
    api_keys.bump_usage(h, 250, prepaid=True)
    api_keys.bump_usage(h, 150, prepaid=True)
    rep = api_keys.usage_report(rec)
    assert rep["billing_mode"] == "prepaid"
    assert rep["prepaid_balance"] == 9600
    assert rep["characters_used_this_period"] == 400
    assert rep["requests_this_period"] == 2
    assert rep["daily"][-1]["characters"] == 400 and rep["daily"][-1]["requests"] == 2
    assert "monthly_quota" not in rep

    monthly = api_keys.create_api_key("T", _unique_email(), "api_pro", 1000)["record"]
    assert api_keys.usage_report(monthly)["monthly_quota"] == 1000


def test_rotate_key_keeps_usage_balance_and_settings():
    """Regression: rotation used to reset the month's usage to zero (and would
    have wiped a prepaid balance) because usage is keyed by key hash."""
    original = _wholesale(billing_mode="prepaid", rpm_limit=30,
                          allowed_voices="ur-PK-UzmaNeural", notes="contract #7")
    old = original["record"]
    api_keys.top_up_balance(old["key_hash"], 5000)
    api_keys.bump_usage(old["key_hash"], 1200, prepaid=True)

    rotated = api_keys.rotate_key(old["id"])
    new = rotated["record"]
    assert new["key_hash"] != old["key_hash"]
    assert new["billing_mode"] == "prepaid" and new["rpm_limit"] == 30
    assert new["allowed_voices"] == ["ur-PK-UzmaNeural"] and new["notes"] == "contract #7"
    usage = api_keys.get_usage(new["key_hash"])
    assert usage["balance"] == 3800
    assert usage["chars_used"] == 1200


def test_rotate_monthly_key_does_not_reset_usage():
    rec = api_keys.create_api_key("T", _unique_email(), "api_free", 10000)["record"]
    api_keys.bump_usage(rec["key_hash"], 9000)
    new = api_keys.rotate_key(rec["id"])["record"]
    assert api_keys.get_usage(new["key_hash"])["chars_used"] == 9000


def test_update_key_settings_only_changes_given_fields():
    rec = _wholesale(rpm_limit=10, notes="keep me")["record"]
    assert api_keys.update_key_settings(rec["id"], rpm_limit=99, billing_mode="prepaid")
    updated = next(k for k in api_keys.find_keys_by_email(rec["customer_email"]))
    assert updated["rpm_limit"] == 99 and updated["billing_mode"] == "prepaid"
    assert updated["notes"] == "keep me"
    assert not api_keys.update_key_settings("nope", rpm_limit=1)


def test_balance_survives_period_rollover():
    rec = _wholesale(billing_mode="prepaid")["record"]
    h = rec["key_hash"]
    api_keys.top_up_balance(h, 777)
    # Simulate a stale previous-month row
    with __import__("persistence").api_key_usage_transaction(h) as holder:
        u = holder["usage"]; u["period"] = "1999-01"; u["chars_used"] = 55
        holder["usage"] = u
    usage = api_keys.get_usage(h)
    assert usage["chars_used"] == 0 and usage["balance"] == 777
