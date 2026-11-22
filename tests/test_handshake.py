from datetime import datetime, timedelta, timezone

import pytest

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


# ==============================================================================
# Route-level integration tests for pickup handshake
# ==============================================================================
import uuid
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from fastapi.responses import Response

from app.handshake.routes import (
    VerifyCodeRequest,
    get_pickup_code,
    verify_pickup_code,
)
from app.claims.routes import (
    get_claim_code_alias,
    verify_claim_pickup_alias,
)


def _mock_db_for_get_code(
    claim_id,
    donor_id,
    claim_status="active",
    listing_status="claimed",
    claim_expired=False,
    food_expired=False,
    handshake_exists=True,
    verified_at=None,
    invalidated_at=None,
    different_donor=False,
):
    now = datetime.now(timezone.utc)
    claim_expiry = (now - timedelta(minutes=5)) if claim_expired else (now + timedelta(minutes=10))
    food_expiry = (now - timedelta(minutes=5)) if food_expired else (now + timedelta(hours=2))

    listing_id = str(uuid.uuid4())
    actual_donor = str(uuid.uuid4()) if different_donor else str(donor_id)

    db = MagicMock()

    def table_router(table_name):
        tbl = MagicMock()
        if table_name == "claims":
            claim_row = {
                "id": str(claim_id),
                "listing_id": listing_id,
                "status": claim_status,
                "expires_at": claim_expiry.isoformat(),
            }
            tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [claim_row]
        elif table_name == "food_listings":
            listing_row = {
                "id": listing_id,
                "donor_id": actual_donor,
                "status": listing_status,
                "safe_until": food_expiry.isoformat(),
            }
            tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [listing_row]
        elif table_name == "pickup_handshakes":
            hs_row = {
                "claim_id": str(claim_id),
                "verified_at": verified_at,
                "invalidated_at": invalidated_at,
            } if handshake_exists else None
            tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [hs_row] if hs_row else []
        return tbl

    db.table.side_effect = table_router
    return db


def test_get_pickup_code_authorized_donor_success():
    cid = uuid.uuid4()
    did = uuid.uuid4()
    donor = {"id": str(did), "role": "donor"}
    resp = Response()
    db = _mock_db_for_get_code(cid, did)

    with patch("app.handshake.routes.get_supabase", return_value=db):
        result = get_pickup_code(cid, resp, donor=donor)

    assert result["claim_id"] == str(cid)
    assert len(result["pickup_code"]) == 4 and result["pickup_code"].isdigit()
    assert resp.headers["Cache-Control"] == "no-store"


def test_get_pickup_code_unrelated_donor_forbidden():
    cid = uuid.uuid4()
    did = uuid.uuid4()
    donor = {"id": str(did), "role": "donor"}
    resp = Response()
    db = _mock_db_for_get_code(cid, did, different_donor=True)

    with patch("app.handshake.routes.get_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc_info:
            get_pickup_code(cid, resp, donor=donor)
        assert exc_info.value.status_code == 404


def test_get_pickup_code_inactive_claim_conflict():
    cid = uuid.uuid4()
    did = uuid.uuid4()
    donor = {"id": str(did), "role": "donor"}
    resp = Response()
    db = _mock_db_for_get_code(cid, did, claim_status="completed")

    with patch("app.handshake.routes.get_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc_info:
            get_pickup_code(cid, resp, donor=donor)
        assert exc_info.value.status_code == 409


def test_get_pickup_code_expired_claim_gone():
    cid = uuid.uuid4()
    did = uuid.uuid4()
    donor = {"id": str(did), "role": "donor"}
    resp = Response()
    db = _mock_db_for_get_code(cid, did, claim_expired=True)

    with patch("app.handshake.routes.get_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc_info:
            get_pickup_code(cid, resp, donor=donor)
        assert exc_info.value.status_code == 410


def test_get_pickup_code_already_verified():
    cid = uuid.uuid4()
    did = uuid.uuid4()
    donor = {"id": str(did), "role": "donor"}
    resp = Response()
    db = _mock_db_for_get_code(cid, did, verified_at=datetime.now(timezone.utc).isoformat())

    with patch("app.handshake.routes.get_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc_info:
            get_pickup_code(cid, resp, donor=donor)
        assert exc_info.value.status_code == 409


def test_get_pickup_code_invalidated():
    cid = uuid.uuid4()
    did = uuid.uuid4()
    donor = {"id": str(did), "role": "donor"}
    resp = Response()
    db = _mock_db_for_get_code(cid, did, invalidated_at=datetime.now(timezone.utc).isoformat())

    with patch("app.handshake.routes.get_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc_info:
            get_pickup_code(cid, resp, donor=donor)
        assert exc_info.value.status_code == 409


def test_verify_pickup_code_atomic_success():
    cid = uuid.uuid4()
    rid = str(uuid.uuid4())
    receiver = {"id": rid, "role": "receiver", "is_verified": True, "approval_status": "approved"}
    req = VerifyCodeRequest(code="1234")

    db = MagicMock()
    now_iso = datetime.now(timezone.utc).isoformat()
    db.rpc.return_value.execute.return_value.data = {
        "success": True,
        "code": "OK",
        "claim_id": str(cid),
        "listing_id": str(uuid.uuid4()),
        "claim_status": "completed",
        "listing_status": "picked_up",
        "verified_at": now_iso,
    }

    with patch("app.handshake.routes.get_supabase", return_value=db):
        result = verify_pickup_code(cid, req, receiver=receiver)

    assert result["claim_status"] == "completed"
    assert result["listing_status"] == "picked_up"
    assert result["verified_at"] == now_iso

    rpc_call = db.rpc.call_args
    assert rpc_call[0][0] == "verify_pickup_handshake"
    assert rpc_call[0][1]["p_claim_id"] == str(cid)
    assert rpc_call[0][1]["p_receiver_id"] == rid
    assert len(rpc_call[0][1]["p_candidate_hash"]) == 64


@pytest.mark.parametrize("outcome,expected_status", [
    ("WRONG_CODE", 400),
    ("LOCKED", 423),
    ("EXPIRED", 410),
    ("FORBIDDEN", 403),
    ("NOT_FOUND", 404),
    ("ALREADY_USED", 409),
    ("INVALIDATED", 409),
    ("NO_HANDSHAKE", 409),
    ("CONFLICT", 409),
])
def test_verify_pickup_code_error_mappings(outcome, expected_status):
    cid = uuid.uuid4()
    rid = str(uuid.uuid4())
    receiver = {"id": rid, "role": "receiver", "is_verified": True, "approval_status": "approved"}
    req = VerifyCodeRequest(code="0000")

    db = MagicMock()
    db.rpc.return_value.execute.return_value.data = {
        "success": False,
        "code": outcome,
    }

    with patch("app.handshake.routes.get_supabase", return_value=db):
        with pytest.raises(HTTPException) as exc_info:
            verify_pickup_code(cid, req, receiver=receiver)
        assert exc_info.value.status_code == expected_status


def test_claims_aliases_route_to_handshake():
    cid = uuid.uuid4()
    did = uuid.uuid4()
    rid = str(uuid.uuid4())

    donor = {"id": str(did), "role": "donor"}
    receiver = {"id": rid, "role": "receiver", "is_verified": True, "approval_status": "approved"}
    req = VerifyCodeRequest(code="1234")

    db_code = _mock_db_for_get_code(cid, did)
    resp = Response()
    with patch("app.handshake.routes.get_supabase", return_value=db_code):
        res_code = get_claim_code_alias(cid, resp, donor=donor)
    assert res_code["claim_id"] == str(cid)

    db_verify = MagicMock()
    db_verify.rpc.return_value.execute.return_value.data = {
        "success": True,
        "code": "OK",
        "claim_id": str(cid),
        "listing_id": str(uuid.uuid4()),
        "claim_status": "completed",
        "listing_status": "picked_up",
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
    with patch("app.handshake.routes.get_supabase", return_value=db_verify):
        res_verify = verify_claim_pickup_alias(cid, req, user=receiver)
    assert res_verify["claim_status"] == "completed"
