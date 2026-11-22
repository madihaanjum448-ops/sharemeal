"""Focused unit tests for wiring timeout-strike processing into the expiry worker.

These use mocks only (no network, no real credentials). Whether a given claim is ELIGIBLE and whether
repeated runs are IDEMPOTENT is decided by the database function, and is proven against real
PostgreSQL in tests/sql/test_timeout_strikes_sql.py.
"""
from unittest.mock import MagicMock, call, patch

import pytest

from app.jobs.expiry_worker import run_expiry_and_timeout_sweep
from app.jobs.timeout_strikes import TimeoutStrikeError, apply_timeout_strikes

SWEEP = {"expired_claims": 1, "reopened_listings": 1, "expired_listings": 0}


def response(data):
    r = MagicMock()
    r.data = data
    return r


def make_db(*results):
    """results: a payload (returned) or an Exception (raised), one per RPC call, in order."""
    db = MagicMock()
    effects = [r if isinstance(r, Exception) else response(r) for r in results]
    db.rpc.return_value.execute.side_effect = effects
    return db


def run(db):
    with patch("app.jobs.expiry_worker.get_supabase", return_value=db):
        return run_expiry_and_timeout_sweep()


# ---- eligible path: strikes are applied after the sweep, response unchanged ------------------
def test_strikes_applied_after_sweep_and_sweep_result_returned_unchanged():
    db = make_db(SWEEP, {"strikes_added": 1})
    result = run(db)
    assert result == SWEEP
    assert list(result) == ["expired_claims", "reopened_listings", "expired_listings"]  # no new keys
    assert db.rpc.call_args_list == [
        call("process_expired_claims_and_listings", {}),
        call("apply_timeout_strikes", {}),
    ]


def test_strike_step_reuses_the_workers_client():
    db = make_db(SWEEP, {"strikes_added": 0})
    with patch("app.jobs.expiry_worker.get_supabase", return_value=db) as getter:
        run_expiry_and_timeout_sweep()
    assert getter.call_count == 1   # one client for both steps; no second connection / credentials


def test_zero_strikes_added_is_a_normal_success():
    db = make_db(SWEEP, {"strikes_added": 0})
    assert run(db) == SWEEP


# ---- ineligible: nothing special in Python, the DB decides; worker must not fabricate strikes -
def test_worker_never_writes_strikes_itself():
    db = make_db(SWEEP, {"strikes_added": 0})
    run(db)
    db.table.assert_not_called()    # strikes are only ever created by the apply_timeout_strikes RPC


# ---- duplicate execution ------------------------------------------------------------------
def test_repeated_runs_each_call_both_steps_and_stay_compatible():
    db = make_db(SWEEP, {"strikes_added": 1}, SWEEP, {"strikes_added": 0})
    assert run(db) == SWEEP
    assert run(db) == SWEEP
    names = [c.args[0] for c in db.rpc.call_args_list]
    assert names == ["process_expired_claims_and_listings", "apply_timeout_strikes"] * 2


# ---- database errors ----------------------------------------------------------------------
def test_sweep_error_propagates_and_strikes_are_not_attempted():
    db = make_db(RuntimeError("DB unavailable"))
    with pytest.raises(RuntimeError, match="DB unavailable"):
        run(db)
    assert [c.args[0] for c in db.rpc.call_args_list] == ["process_expired_claims_and_listings"]


def test_sweep_unexpected_response_stops_before_strikes():
    db = make_db(["not", "a dict"])
    with pytest.raises(RuntimeError, match="unexpected response"):
        run(db)
    assert db.rpc.call_count == 1


def test_strike_rpc_error_is_raised_not_swallowed_and_sweep_not_repeated():
    secret = "https://x.supabase.co key=SERVICE-ROLE-SECRET"
    db = make_db(SWEEP, RuntimeError(secret))
    with pytest.raises(TimeoutStrikeError) as info:
        run(db)
    assert "after the expiry sweep completed" in str(info.value)
    assert "SERVICE-ROLE-SECRET" not in str(info.value)          # message never echoes DB/credential text
    assert isinstance(info.value.__cause__, RuntimeError)         # original kept for server-side logs
    assert db.rpc.call_count == 2


@pytest.mark.parametrize("bad", [None, [], ["x"], "ok", {}, {"strikes_added": "1"}, {"other": 1}])
def test_malformed_strike_response_is_rejected(bad):
    db = make_db(SWEEP, bad)
    with pytest.raises(TimeoutStrikeError, match="unexpected response"):
        run(db)


def test_timeout_strike_error_is_a_runtime_error():
    assert issubclass(TimeoutStrikeError, RuntimeError)   # existing `except RuntimeError` callers still work


def test_apply_timeout_strikes_direct_contract():
    db = make_db({"strikes_added": 3})
    assert apply_timeout_strikes(db) == {"strikes_added": 3}
    db.rpc.assert_called_once_with("apply_timeout_strikes", {})


# ---- contract with the pure strike service (Member 2) ------------------------------------------
def test_event_type_constant_matches_pure_strike_service():
    from app.strikes.service import EVENT_TIMEOUT
    assert EVENT_TIMEOUT == "timeout"   # value hard-coded in the migration's INSERT and CHECK
