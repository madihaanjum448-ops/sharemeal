from datetime import datetime, timedelta, timezone

from app.handshake.service import (
    ALREADY_USED, EXPIRED, LOCKED, MAX_ATTEMPTS, OK, WRONG,
    generate_code, hash_code, start_handshake, verify_handshake,
)

SECRET = "test-secret"
NOW = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
LATER = NOW + timedelta(minutes=15)


def fresh(code="1234"):
    return start_handshake("claim-1", SECRET, LATER, code=code)


def test_generated_code_is_four_digits():
    for _ in range(50):
        code = generate_code()
        assert len(code) == 4 and code.isdigit()


def test_plain_code_is_never_stored():
    record, code = fresh("1234")
    assert code == "1234"
    assert "1234" not in repr(record)


def test_same_code_hashes_differently_per_claim():
    assert hash_code("1234", "claim-1", SECRET) != hash_code("1234", "claim-2", SECRET)


def test_correct_code_completes():
    record, _ = fresh()
    updated, result = verify_handshake(record, "1234", SECRET, NOW)
    assert result == OK and updated.verified_at == NOW


def test_wrong_code_counts_attempt():
    record, _ = fresh()
    updated, result = verify_handshake(record, "0000", SECRET, NOW)
    assert result == WRONG and updated.attempts == 1 and updated.verified_at is None


def test_five_wrong_attempts_lock_even_for_correct_code():
    record, _ = fresh()
    for _ in range(MAX_ATTEMPTS):
        record, result = verify_handshake(record, "0000", SECRET, NOW)
        assert result == WRONG
    record, result = verify_handshake(record, "1234", SECRET, NOW)
    assert result == LOCKED


def test_expired_code_rejected():
    record, _ = fresh()
    _, result = verify_handshake(record, "1234", SECRET, LATER)
    assert result == EXPIRED


def test_replay_after_success_rejected():
    record, _ = fresh()
    record, first = verify_handshake(record, "1234", SECRET, NOW)
    _, second = verify_handshake(record, "1234", SECRET, NOW)
    assert first == OK and second == ALREADY_USED


def test_input_record_not_modified():
    record, _ = fresh()
    verify_handshake(record, "0000", SECRET, NOW)
    assert record.attempts == 0


def test_derived_code_is_four_digits_and_repeatable():
    from app.handshake.service import derive_code
    first = derive_code("claim-1", SECRET)
    assert len(first) == 4 and first.isdigit()
    assert first == derive_code("claim-1", SECRET)


def test_derived_code_differs_by_claim_and_secret():
    from app.handshake.service import derive_code
    assert derive_code("claim-1", SECRET) != derive_code("claim-2", SECRET)
    assert derive_code("claim-1", SECRET) != derive_code("claim-1", "other-secret")


def test_default_code_matches_derived_code():
    from app.handshake.service import derive_code
    record, code = start_handshake("claim-1", SECRET, LATER)
    assert code == derive_code("claim-1", SECRET)
    _, result = verify_handshake(record, code, SECRET, NOW)
    assert result == OK
