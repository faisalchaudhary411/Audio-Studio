import uuid

import accounts


def _unique_email():
    return f"test-{uuid.uuid4().hex[:10]}@example.com"


def test_find_or_create_user_creates_new_account():
    email = _unique_email()
    record, is_new = accounts.find_or_create_user(email, "Test User")
    assert is_new is True
    assert record["email"] == email
    assert record["password_hash"] == ""


def test_find_or_create_user_is_idempotent():
    """A renewal or a Starter->Pro upgrade hits this again — must return
    the SAME account, not create a second one or wipe the password."""
    email = _unique_email()
    accounts.find_or_create_user(email, "Test User")
    accounts.set_password(email, "correct-horse-battery-staple")

    record, is_new = accounts.find_or_create_user(email, "Test User Again")
    assert is_new is False
    # password must survive being "found" again, not get reset
    assert accounts.verify_login(email, "correct-horse-battery-staple") != {}


def test_verify_login_succeeds_with_correct_password():
    email = _unique_email()
    accounts.find_or_create_user(email, "Test User")
    accounts.set_password(email, "hunter2-but-better")
    assert accounts.verify_login(email, "hunter2-but-better") != {}


def test_verify_login_fails_with_wrong_password():
    email = _unique_email()
    accounts.find_or_create_user(email, "Test User")
    accounts.set_password(email, "the-real-password")
    assert accounts.verify_login(email, "totally-wrong-guess") == {}


def test_verify_login_fails_when_no_password_set_yet():
    """Account exists (created at payment time) but customer hasn't used
    the set-password link yet — must fail closed, not treat blank
    password_hash as 'no password required'."""
    email = _unique_email()
    accounts.find_or_create_user(email, "Test User")
    assert accounts.verify_login(email, "") == {}
    assert accounts.verify_login(email, "anything") == {}


def test_verify_login_fails_for_unknown_email():
    assert accounts.verify_login(f"nobody-{uuid.uuid4().hex}@example.com", "whatever") == {}


def test_token_round_trip_set_purpose():
    email = _unique_email()
    accounts.find_or_create_user(email, "Test User")
    token = accounts.issue_token(email, "set")
    result = accounts.consume_token(token)
    assert result == {"email": email, "purpose": "set"}


def test_token_is_single_use():
    email = _unique_email()
    accounts.find_or_create_user(email, "Test User")
    token = accounts.issue_token(email, "reset")
    first = accounts.consume_token(token)
    second = accounts.consume_token(token)
    assert first != {}
    assert second == {}  # replay must fail


def test_unknown_token_fails():
    assert accounts.consume_token("this-token-was-never-issued") == {}
