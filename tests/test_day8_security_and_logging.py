import logging
import uuid
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.auth.schemas import SendOTPRequest, VerifyOTPRequest
from app.auth.routes import send_otp, verify_otp
from app.core.auth import (
    get_current_donor,
    get_current_verified_receiver,
    get_current_admin,
)
from app.claims.routes import ClaimRequest, create_claim
from app.listings.schemas import FoodListingCreate
from app.listings.routes import create_listing
from app.admin.routes import get_pending_receivers
from app.main import global_exception_handler


# ---------------------------------------------------------------------------
# Day 8 Security: Logging Redaction & Secret Hygiene (Tasks 2 & 4)
# ---------------------------------------------------------------------------

def test_logging_send_otp_redacts_credentials(caplog):
    """Ensure send_otp logs only the exception class name and does not leak email or secrets."""
    req = SendOTPRequest(email="confidential.donor@example.com")
    mock_http_req = MagicMock()
    mock_http_req.client.host = "192.168.1.100"

    with patch("app.auth.routes.auth_supabase") as mock_auth, \
         patch("app.auth.routes.enforce_otp_send_limit"), \
         caplog.at_level(logging.INFO, logger="sharemeal.auth"):

        mock_auth.auth.sign_in_with_otp.side_effect = RuntimeError("Supabase network drop")
        
        with pytest.raises(HTTPException) as exc_info:
            send_otp(req, mock_http_req)
        assert exc_info.value.status_code == 503

        # Verify log output: should contain exception name, but NOT the email
        log_text = caplog.text
        assert "RuntimeError" in log_text
        assert "confidential.donor@example.com" not in log_text


def test_logging_verify_otp_redacts_otp_token(caplog):
    """Ensure verify_otp does NOT log the submitted OTP code on verification failure."""
    sensitive_token = "87654321"
    req = VerifyOTPRequest(email="user@example.com", token=sensitive_token)
    mock_http_req = MagicMock()
    mock_http_req.client.host = "192.168.1.100"

    with patch("app.auth.routes.auth_supabase") as mock_auth, \
         patch("app.auth.routes.enforce_otp_send_limit"), \
         caplog.at_level(logging.INFO, logger="sharemeal.auth"):

        mock_auth.auth.verify_otp.side_effect = ValueError("Invalid token code")

        with pytest.raises(HTTPException) as exc_info:
            verify_otp(req, mock_http_req)
        assert exc_info.value.status_code == 401

        log_text = caplog.text
        assert sensitive_token not in log_text


def test_global_exception_handler_sanitizes_errors():
    """Ensure unhandled exceptions return a generic error envelope and do not leak stack traces."""
    import json

    mock_request = MagicMock(spec=Request)
    mock_request.state.request_id = "test-req-id-12345"

    internal_exc = RuntimeError("CRITICAL: database postgresql://admin:secret_pass@db.internal:5432 failed")

    # Coroutine execution without event loop (avoids Windows sandbox loopback socket restrictions)
    coro = global_exception_handler(mock_request, internal_exc)
    try:
        coro.send(None)
        response = None
    except StopIteration as exc:
        response = exc.value

    assert isinstance(response, JSONResponse)
    assert response.status_code == 500

    # Verify response body does NOT contain internal connection string or secret
    body = json.loads(response.body.decode("utf-8"))
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert body["error"]["message"] == "An unexpected internal server error occurred"
    assert body["error"]["request_id"] == "test-req-id-12345"
    assert "secret_pass" not in response.body.decode("utf-8")
    assert "db.internal" not in response.body.decode("utf-8")


# ---------------------------------------------------------------------------
# Day 8 Security: Role Enforcement & Privilege Escalation Prevention (Task 3)
# ---------------------------------------------------------------------------

def test_security_pending_receiver_cannot_claim_food():
    """Pending receiver must be rejected with 403 Forbidden on claim attempt."""
    pending_receiver = {
        "id": "r-pending-1",
        "role": "receiver",
        "approval_status": "pending",
        "is_verified": False,
    }
    with pytest.raises(HTTPException) as exc_info:
        get_current_verified_receiver(pending_receiver)
    assert exc_info.value.status_code == 403
    assert "requires administrator approval" in exc_info.value.detail


def test_security_rejected_receiver_cannot_claim_food():
    """Rejected receiver must be rejected with 403 Forbidden on claim attempt."""
    rejected_receiver = {
        "id": "r-rejected-1",
        "role": "receiver",
        "approval_status": "rejected",
        "is_verified": False,
    }
    with pytest.raises(HTTPException) as exc_info:
        get_current_verified_receiver(rejected_receiver)
    assert exc_info.value.status_code == 403


def test_security_donor_cannot_access_receiver_claim_route():
    """Donor attempting to access receiver claims must be rejected with 403 Forbidden."""
    donor_user = {
        "id": "d-1",
        "role": "donor",
        "approval_status": None,
        "is_verified": True,
    }
    with pytest.raises(HTTPException) as exc_info:
        get_current_verified_receiver(donor_user)
    assert exc_info.value.status_code == 403
    assert "Only recipient organisations" in exc_info.value.detail


def test_security_receiver_cannot_create_food_listing():
    """Receiver attempting to create a listing must be rejected with 403 Forbidden."""
    receiver_user = {
        "id": "r-1",
        "role": "receiver",
        "approval_status": "approved",
        "is_verified": True,
    }
    with pytest.raises(HTTPException) as exc_info:
        get_current_donor(receiver_user)
    assert exc_info.value.status_code == 403
    assert "Only donors can perform this operation" in exc_info.value.detail


def test_security_non_admin_cannot_access_admin_portal():
    """Neither donor nor receiver can access admin endpoints."""
    donor_user = {"id": "d-1", "role": "donor"}
    receiver_user = {"id": "r-1", "role": "receiver"}

    with pytest.raises(HTTPException) as exc1:
        get_current_admin(donor_user)
    assert exc1.value.status_code == 403

    with pytest.raises(HTTPException) as exc2:
        get_current_admin(receiver_user)
    assert exc2.value.status_code == 403
