import logging

import app.handshake.routes as hroutes
from app.handshake.rpc import (
    HandshakeError, confirm_pickup, donor_handshake_code,
    start_handshake_for_claim, start_handshake_or_cancel,
)
from app.handshake.service import derive_code, hash_code
from app.strikes.rpc import run_timeout_strikes
from fastapi import HTTPException, Response

SECRET = "unit-test-secret-1234567890"
CLAIM_ID = "11111111-1111-4111-8111-111111111111"
LISTING_ID = "22222222-2222-4222-8222-222222222222"
RECEIVER = {"id": "33333333-3333-4333-8333-333333333333", "role": "receiver"}
DONOR = {"id": "44444444-4444-4444-8444-444444444444", "role": "donor"}
OTHER_DONOR = {"id": "55555555-5555-4555-8555-555555555555", "role": "donor"}


# ---- a tiny in-memory stand-in for the Supabase client ---------------------------
class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeRpc:
    def __init__(self, client, name, params):
        self.client, self.name, self.params = client, name, params

    def execute(self):
        self.client.rpc_calls.append((self.name, self.params))
        outcome = self.client.rpc_results.get(self.name)
        if isinstance(outcome, Exception):
            raise outcome
        return FakeResult(outcome)


class FakeQuery:
    def __init__(self, client, name):
        self.client, self.name, self.filters, self.limit_n = client, name, [], None

    def select(self, columns="*"):
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def limit(self, n):
        self.limit_n = n
        return self

    def execute(self):
        rows = self.client.tables.get(self.name, [])
        found = [dict(r) for r in rows if all(r.get(c) == v for c, v in self.filters)]
        return FakeResult(found[: self.limit_n] if self.limit_n else found)


class FakeClient:
    def __init__(self, rpc_results=None, tables=None):
        self.rpc_results = rpc_results or {}
        self.tables = tables or {}
        self.rpc_calls = []

    def rpc(self, name, params):
        return FakeRpc(self, name, params)

    def table(self, name):
        return FakeQuery(self, name)


def with_secret(monkeypatch):
    monkeypatch.setenv("HANDSHAKE_SECRET", SECRET)


def error_of(fn, *args):
    try:
        fn(*args)
    except HandshakeError as exc:
        return exc.status_code, exc.detail
    return None


def donor_tables(status="active", handshake="2026-11-20T10:15:00+00:00"):
    return {
        "claims": [{"id": CLAIM_ID, "listing_id": LISTING_ID, "status": status,
                    "handshake_expires_at": handshake}],
        "food_listings": [{"id": LISTING_ID, "donor_id": DONOR["id"]}],
    }


# ---- starting the handshake -----------------------------------------------------------
def test_start_sends_only_the_hash(monkeypatch):
    with_secret(monkeypatch)
    client = FakeClient({"start_claim_handshake": "2026-11-20T10:15:00Z"})
    assert start_handshake_for_claim(client, CLAIM_ID) is True
    name, params = client.rpc_calls[0]
    code = derive_code(CLAIM_ID, SECRET)
    assert name == "start_claim_handshake"
    assert params["p_code_hash"] == hash_code(code, CLAIM_ID, SECRET)
    assert len(params["p_code_hash"]) == 64
    assert code not in (params["p_claim_id"], params["p_code_hash"])


def test_start_reports_failure_when_nothing_was_started(monkeypatch):
    with_secret(monkeypatch)
    assert start_handshake_for_claim(FakeClient({"start_claim_handshake": None}), CLAIM_ID) is False
    assert start_handshake_for_claim(FakeClient({"start_claim_handshake": RuntimeError("x")}), CLAIM_ID) is False


def test_start_is_skipped_when_the_secret_is_missing_or_short(monkeypatch):
    monkeypatch.delenv("HANDSHAKE_SECRET", raising=False)
    client = FakeClient()
    assert start_handshake_for_claim(client, CLAIM_ID) is True and client.rpc_calls == []
    monkeypatch.setenv("HANDSHAKE_SECRET", "short")
    assert start_handshake_for_claim(client, CLAIM_ID) is True and client.rpc_calls == []


def test_start_normalizes_the_claim_id(monkeypatch):
    with_secret(monkeypatch)
    client = FakeClient({"start_claim_handshake": "t"})
    start_handshake_for_claim(client, CLAIM_ID.upper())
    assert client.rpc_calls[0][1]["p_claim_id"] == CLAIM_ID
    assert start_handshake_for_claim(client, "not-a-uuid") is False


def test_failed_start_cancels_the_claim(monkeypatch):
    with_secret(monkeypatch)
    client = FakeClient({"start_claim_handshake": None, "cancel_food_claim": {"success": True}})
    assert start_handshake_or_cancel(client, CLAIM_ID, RECEIVER["id"]) is False
    assert client.rpc_calls[1] == (
        "cancel_food_claim", {"p_claim_id": CLAIM_ID, "p_receiver_id": RECEIVER["id"]})


def test_successful_start_does_not_cancel(monkeypatch):
    with_secret(monkeypatch)
    client = FakeClient({"start_claim_handshake": "t"})
    assert start_handshake_or_cancel(client, CLAIM_ID, RECEIVER["id"]) is True
    assert [name for name, _ in client.rpc_calls] == ["start_claim_handshake"]


def test_a_failing_cancel_never_raises(monkeypatch):
    with_secret(monkeypatch)
    client = FakeClient({"start_claim_handshake": None, "cancel_food_claim": RuntimeError("boom")})
    assert start_handshake_or_cancel(client, CLAIM_ID, RECEIVER["id"]) is False


# ---- confirming a pickup --------------------------------------------------------------
def test_confirm_hashes_the_code_and_uses_the_logged_in_user(monkeypatch):
    with_secret(monkeypatch)
    client = FakeClient({"confirm_claim_pickup": "ok"})
    result = confirm_pickup(client, CLAIM_ID, RECEIVER, "4073")
    assert result == {"status": "completed", "claim_id": CLAIM_ID}
    assert client.rpc_calls == [("confirm_claim_pickup", {
        "p_claim_id": CLAIM_ID,
        "p_actor_id": RECEIVER["id"],
        "p_candidate_hash": hash_code("4073", CLAIM_ID, SECRET),
    })]


def test_malformed_codes_never_reach_the_database(monkeypatch):
    with_secret(monkeypatch)
    client = FakeClient({"confirm_claim_pickup": "ok"})
    for bad in ("12", "12345", "abcd", "12 4", "1234\n", "١٢٣٤", 1234, None, ["1234"]):
        assert error_of(confirm_pickup, client, CLAIM_ID, RECEIVER, bad) == (422, "invalid_code_format")
    assert client.rpc_calls == []


def test_every_database_result_maps_to_a_status(monkeypatch):
    with_secret(monkeypatch)
    expected = {
        "wrong_code": (400, "wrong_code"), "locked": (423, "locked"),
        "expired": (410, "expired"), "already_used": (409, "already_used"),
        "claim_not_active": (409, "claim_not_active"), "no_handshake": (409, "no_handshake"),
        "not_found": (404, "not_found"),
    }
    for outcome, status in expected.items():
        client = FakeClient({"confirm_claim_pickup": outcome})
        assert error_of(confirm_pickup, client, CLAIM_ID, RECEIVER, "1234") == status


def test_unexpected_or_failing_database_gives_503_without_leaking(monkeypatch):
    with_secret(monkeypatch)
    assert error_of(confirm_pickup, FakeClient({"confirm_claim_pickup": "weird"}), CLAIM_ID, RECEIVER, "1234") \
        == (503, "pickup_service_unavailable")
    failing = FakeClient({"confirm_claim_pickup": RuntimeError("password=XYZ code 1234")})
    status, detail = error_of(confirm_pickup, failing, CLAIM_ID, RECEIVER, "1234")
    assert status == 503 and "XYZ" not in detail and "1234" not in detail


def test_confirm_needs_the_secret_and_a_valid_claim_id(monkeypatch):
    monkeypatch.delenv("HANDSHAKE_SECRET", raising=False)
    assert error_of(confirm_pickup, FakeClient(), CLAIM_ID, RECEIVER, "1234") == (503, "handshake_not_configured")
    with_secret(monkeypatch)
    assert error_of(confirm_pickup, FakeClient(), "nope", RECEIVER, "1234") == (404, "not_found")


def test_the_plain_code_is_never_logged(monkeypatch):
    with_secret(monkeypatch)
    records = []

    class Catch(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    handler = Catch()
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.DEBUG)
    try:
        client = FakeClient({"confirm_claim_pickup": RuntimeError("code 4073 failed")})
        error_of(confirm_pickup, client, CLAIM_ID, RECEIVER, "4073")
        start_handshake_for_claim(FakeClient({"start_claim_handshake": RuntimeError("boom")}), CLAIM_ID)
    finally:
        logging.getLogger().removeHandler(handler)
    assert records and all("4073" not in message for message in records)


# ---- the donor reading the code ------------------------------------------------------------
def test_owning_donor_gets_the_code_and_nothing_else(monkeypatch):
    with_secret(monkeypatch)
    result = donor_handshake_code(FakeClient(tables=donor_tables()), CLAIM_ID, DONOR)
    assert set(result.keys()) == {"code", "expires_at"}
    assert result["code"] == derive_code(CLAIM_ID, SECRET)


def test_other_donors_and_unknown_claims_look_identical(monkeypatch):
    with_secret(monkeypatch)
    client = FakeClient(tables=donor_tables())
    assert error_of(donor_handshake_code, client, CLAIM_ID, OTHER_DONOR) == (404, "not_found")
    other_claim = "66666666-6666-4666-8666-666666666666"
    assert error_of(donor_handshake_code, client, other_claim, DONOR) == (404, "not_found")


def test_donor_code_needs_an_active_claim_with_a_handshake(monkeypatch):
    with_secret(monkeypatch)
    assert error_of(donor_handshake_code, FakeClient(tables=donor_tables(status="completed")),
                    CLAIM_ID, DONOR) == (409, "claim_not_active")
    assert error_of(donor_handshake_code, FakeClient(tables=donor_tables(handshake=None)),
                    CLAIM_ID, DONOR) == (409, "no_handshake")


# ---- strikes wrapper -------------------------------------------------------------------------
def test_timeout_strike_run_returns_the_count():
    assert run_timeout_strikes(FakeClient({"apply_timeout_strikes": 2})) == 2


def test_timeout_strike_run_never_raises():
    assert run_timeout_strikes(FakeClient({"apply_timeout_strikes": RuntimeError("down")})) is None
    assert run_timeout_strikes(FakeClient({"apply_timeout_strikes": {"unexpected": 1}})) is None
    assert run_timeout_strikes(FakeClient({"apply_timeout_strikes": True})) is None


# ---- the route functions -------------------------------------------------------------------------
def test_confirm_route_returns_the_result_with_no_store(monkeypatch):
    with_secret(monkeypatch)
    client = FakeClient({"confirm_claim_pickup": "ok"})
    monkeypatch.setattr(hroutes, "get_supabase", lambda: client)
    response = Response()
    result = hroutes.confirm_pickup_route(
        claim_id=CLAIM_ID, response=response, payload={"code": "1234"}, user=RECEIVER)
    assert result["status"] == "completed"
    assert response.headers.get("Cache-Control") == "no-store"


def test_confirm_route_turns_errors_into_http_exceptions(monkeypatch):
    with_secret(monkeypatch)
    monkeypatch.setattr(hroutes, "get_supabase", lambda: FakeClient({"confirm_claim_pickup": "locked"}))
    try:
        hroutes.confirm_pickup_route(
            claim_id=CLAIM_ID, response=Response(), payload={"code": "1234"}, user=RECEIVER)
    except HTTPException as exc:
        assert exc.status_code == 423 and exc.detail == "locked"
    else:
        raise AssertionError("expected HTTPException")


def test_donor_route_sets_no_store(monkeypatch):
    with_secret(monkeypatch)
    monkeypatch.setattr(hroutes, "get_supabase", lambda: FakeClient(tables=donor_tables()))
    response = Response()
    result = hroutes.donor_handshake_code_route(claim_id=CLAIM_ID, response=response, user=DONOR)
    assert result["code"] == derive_code(CLAIM_ID, SECRET)
    assert response.headers.get("Cache-Control") == "no-store"


# ---- the hook inside create_claim (Member 1's route) ----------------------------------
def _claim_user():
    return {"id": RECEIVER["id"], "role": "receiver", "is_verified": True, "approval_status": "approved"}


def _claim_payload(listing_id):
    return {"success": True, "claim_id": CLAIM_ID, "listing_id": str(listing_id), "status": "active"}


def test_create_claim_starts_the_handshake_and_hides_the_code(monkeypatch):
    import uuid
    from unittest.mock import patch
    from app.claims.routes import ClaimRequest, create_claim

    with_secret(monkeypatch)
    listing_id = uuid.uuid4()
    claim = _claim_payload(listing_id)
    client = FakeClient({"claim_food_listing": claim, "start_claim_handshake": "2026-11-20T10:15:00Z"})
    with patch("app.claims.routes.get_supabase", return_value=client):
        result = create_claim(ClaimRequest(listing_id=listing_id), user=_claim_user())
    assert [name for name, _ in client.rpc_calls] == ["claim_food_listing", "start_claim_handshake"]
    assert result["claim"] == claim
    assert "handshake" not in str(result).lower()
    assert derive_code(CLAIM_ID, SECRET) not in [str(v) for v in result["claim"].values()]


def test_create_claim_is_cancelled_when_the_handshake_cannot_start(monkeypatch):
    import uuid
    from unittest.mock import patch
    from app.claims.routes import ClaimRequest, create_claim

    with_secret(monkeypatch)
    listing_id = uuid.uuid4()
    client = FakeClient({
        "claim_food_listing": _claim_payload(listing_id),
        "start_claim_handshake": None,
        "cancel_food_claim": {"success": True},
    })
    with patch("app.claims.routes.get_supabase", return_value=client):
        try:
            create_claim(ClaimRequest(listing_id=listing_id), user=_claim_user())
        except HTTPException as exc:
            assert exc.status_code == 503
        else:
            raise AssertionError("expected HTTPException")
    assert [name for name, _ in client.rpc_calls] == [
        "claim_food_listing", "start_claim_handshake", "cancel_food_claim"]


def test_create_claim_is_unchanged_when_no_secret_is_configured(monkeypatch):
    import uuid
    from unittest.mock import patch
    from app.claims.routes import ClaimRequest, create_claim

    monkeypatch.delenv("HANDSHAKE_SECRET", raising=False)
    listing_id = uuid.uuid4()
    claim = dict(_claim_payload(listing_id), claim_id="claim-uuid-1")    # not a real UUID, as in the old tests
    client = FakeClient({"claim_food_listing": claim})
    with patch("app.claims.routes.get_supabase", return_value=client):
        result = create_claim(ClaimRequest(listing_id=listing_id), user=_claim_user())
    assert result["claim"] == claim
    assert [name for name, _ in client.rpc_calls] == ["claim_food_listing"]
