from datetime import datetime, timezone

from app.strikes.service import (
    EVENT_ADMIN_CLEAR, EVENT_TIMEOUT, admin_clear_flag, is_flagged,
    record_timeout_strike, strike_count,
)

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)


def add(events, receiver, claim):
    events, _ = record_timeout_strike(events, receiver, claim, NOW)
    return events


def test_first_timeout_adds_one_strike():
    events, added = record_timeout_strike([], "r1", "c1", NOW)
    assert added is True and strike_count(events, "r1") == 1


def test_retried_job_does_not_double_count():
    events, _ = record_timeout_strike([], "r1", "c1", NOW)
    events, added = record_timeout_strike(events, "r1", "c1", NOW)
    assert added is False and strike_count(events, "r1") == 1


def test_different_claims_count_separately():
    events = add(add([], "r1", "c1"), "r1", "c2")
    assert strike_count(events, "r1") == 2


def test_flagged_at_three_not_at_two():
    events = add(add([], "r1", "c1"), "r1", "c2")
    assert is_flagged(events, "r1") is False
    events = add(events, "r1", "c3")
    assert is_flagged(events, "r1") is True


def test_other_receivers_unaffected():
    events = add(add(add([], "r1", "c1"), "r1", "c2"), "r1", "c3")
    assert is_flagged(events, "r1") is True
    assert strike_count(events, "r2") == 0 and is_flagged(events, "r2") is False


def test_admin_clear_resets_count_and_unflags():
    events = add(add(add([], "r1", "c1"), "r1", "c2"), "r1", "c3")
    events = admin_clear_flag(events, "r1", "admin-1", NOW)
    assert strike_count(events, "r1") == 0 and is_flagged(events, "r1") is False


def test_strikes_after_clear_count_again():
    events = add(add(add([], "r1", "c1"), "r1", "c2"), "r1", "c3")
    events = admin_clear_flag(events, "r1", "admin-1", NOW)
    events = add(events, "r1", "c4")
    assert strike_count(events, "r1") == 1


def test_history_is_kept_after_clear():
    events = add([], "r1", "c1")
    events = admin_clear_flag(events, "r1", "admin-1", NOW)
    assert len(events) == 2
    assert events[1].event_type == EVENT_ADMIN_CLEAR


def test_audit_fields_recorded():
    events, _ = record_timeout_strike([], "r1", "c1", NOW, reason="no show")
    e = events[0]
    assert (e.receiver_id, e.claim_id, e.event_type, e.reason, e.created_at) == (
        "r1", "c1", EVENT_TIMEOUT, "no show", NOW)


def test_input_list_not_modified():
    original = []
    record_timeout_strike(original, "r1", "c1", NOW)
    assert original == []
