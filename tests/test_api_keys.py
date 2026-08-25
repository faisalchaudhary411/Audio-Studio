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
