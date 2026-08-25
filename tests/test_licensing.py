"""
test_licensing.py — covers plan mapping specifically because that's where
a real production bug was found and fixed: fs_callback minted every
Freemius purchase as plain "pro" because create_subscription_key was
being called without a plan= argument at all, silently defaulting every
Pro+ customer to Pro. These tests exist so that exact mistake — passing
the wrong plan, or forgetting to pass one — fails a test instead of
shipping unnoticed again.
"""
import uuid

import licensing


def _unique_email():
    return f"test-{uuid.uuid4().hex[:10]}@example.com"


def test_create_subscription_key_stores_pro_plan():
    email = _unique_email()
    key = licensing.create_subscription_key("Test User", email, plan="pro")
    assert licensing._keys()[key]["plan"] == "pro"


def test_create_subscription_key_stores_pro_plus_plan():
    email = _unique_email()
    key = licensing.create_subscription_key("Test User", email, plan="pro_plus")
    assert licensing._keys()[key]["plan"] == "pro_plus"


def test_create_subscription_key_invalid_plan_falls_back_to_pro():
    """An unrecognized plan string shouldn't silently create a key with a
    made-up plan value that nothing else in the app knows how to handle."""
    email = _unique_email()
    key = licensing.create_subscription_key("Test User", email, plan="not_a_real_plan")
    assert licensing._keys()[key]["plan"] == "pro"


def test_create_subscription_key_default_plan_is_pro():
    """Guards the exact shape of the original bug: calling this WITHOUT a
    plan= argument at all must default to "pro", not crash and not
    silently store something else."""
    email = _unique_email()
    key = licensing.create_subscription_key("Test User", email)
    assert licensing._keys()[key]["plan"] == "pro"


def test_find_key_by_email_returns_most_recent():
    email = _unique_email()
    older_key = licensing.create_subscription_key("Test User", email, plan="pro")
    licensing._keys()[older_key]["created"] = "2020-01-01 00:00"
    persistence_save = licensing._save
    persistence_save(licensing._keys())

    newer_key = licensing.create_subscription_key("Test User", email, plan="pro_plus")

    found = licensing.find_key_by_email(email)
    assert found == newer_key


def test_find_key_by_email_no_match_returns_empty_string():
    assert licensing.find_key_by_email(f"nobody-{uuid.uuid4().hex}@example.com") == ""


def test_find_key_by_freemius_id_round_trip():
    email = _unique_email()
    fs_id = f"fs-{uuid.uuid4().hex[:12]}"
    key = licensing.create_subscription_key("Test User", email, plan="pro", freemius_license_id=fs_id)
    assert licensing.find_key_by_freemius_id(fs_id) == key


def test_find_key_by_freemius_id_empty_input():
    assert licensing.find_key_by_freemius_id("") == ""
