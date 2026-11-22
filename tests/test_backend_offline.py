import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.config import Settings
from app.core.auth import (
    get_current_user,
    get_current_donor,
    get_current_verified_receiver,
    get_current_admin,
)
from app.auth.schemas import SendOTPRequest, VerifyOTPRequest
from app.auth.routes import send_otp, verify_otp
from app.listings.schemas import FoodListingCreate, FoodListingUpdate
from app.listings.routes import (
    create_listing,
    get_available_listings,
    get_listing_details,
    get_my_listings,
    update_listing,
    cancel_listing,
)
from app.claims.routes import (
    ClaimRequest,
    create_claim,
    get_my_claims,
    cancel_claim,
)
from app.admin.routes import (
    get_pending_receivers,
    get_receiver_details,
    approve_receiver,
    reject_receiver,
)
from app.main import root, health, trigger_expiry_sweep


# ---------------------------------------------------------------------------
# Section 1: Settings and Configuration (X-01)
# ---------------------------------------------------------------------------

def test_settings_validate_success():
    s = Settings()
    s.SUPABASE_URL = "https://example.supabase.co"
    s.SUPABASE_KEY = "test-key"
    s.SUPABASE_ANON_KEY = "test-anon-key"
    s.EXPIRY_SWEEP_INTERVAL_SECONDS = 60
    s.validate()  # should not raise


def test_settings_validate_missing_keys():
    s = Settings()
    s.SUPABASE_URL = ""
    s.SUPABASE_KEY = ""
    s.SUPABASE_ANON_KEY = ""
    with pytest.raises(RuntimeError) as exc_info:
        s.validate()
    assert "Missing required environment variables" in str(exc_info.value)


def test_settings_validate_non_https():
    s = Settings()
    s.SUPABASE_URL = "http://insecure.supabase.co"
    s.SUPABASE_KEY = "test-key"
    s.SUPABASE_ANON_KEY = "test-anon-key"
    with pytest.raises(RuntimeError) as exc_info:
        s.validate()
    assert "must be an HTTPS URL" in str(exc_info.value)


def test_settings_validate_sweep_interval():
    s = Settings()
    s.SUPABASE_URL = "https://example.supabase.co"
    s.SUPABASE_KEY = "test-key"
    s.SUPABASE_ANON_KEY = "test-anon-key"
    s.EXPIRY_SWEEP_INTERVAL_SECONDS = 10
    with pytest.raises(RuntimeError) as exc_info:
        s.validate()
    assert "EXPIRY_SWEEP_INTERVAL_SECONDS must be at least 15" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Section 2: Auth and Role Dependencies (X-03, X-04)
# ---------------------------------------------------------------------------

def test_auth_get_current_user_invalid_token():
    mock_creds = MagicMock()
    mock_creds.credentials = "bad-token"
    with patch("app.core.auth.auth_supabase") as mock_auth:
        mock_auth.auth.get_user.side_effect = Exception("Invalid token")
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_creds)
        assert exc_info.value.status_code == 401


def test_auth_get_current_user_profile_db_error():
    mock_creds = MagicMock()
    mock_creds.credentials = "valid-token"
    with patch("app.core.auth.auth_supabase") as mock_auth, \
         patch("app.core.auth.get_supabase") as mock_db:
        mock_user = MagicMock()
        mock_user.id = "user-uuid"
        mock_auth.auth.get_user.return_value.user = mock_user
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = Exception("DB timeout")
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_creds)
        assert exc_info.value.status_code == 503
        assert "Profile service temporarily unavailable" in exc_info.value.detail


def test_auth_get_current_user_profile_not_found():
    mock_creds = MagicMock()
    mock_creds.credentials = "valid-token"
    with patch("app.core.auth.auth_supabase") as mock_auth, \
         patch("app.core.auth.get_supabase") as mock_db:
        mock_user = MagicMock()
        mock_user.id = "user-uuid"
        mock_auth.auth.get_user.return_value.user = mock_user
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_creds)
        assert exc_info.value.status_code == 403


def test_auth_get_current_donor_guard():
    assert get_current_donor({"id": "d1", "role": "donor"}) == {"id": "d1", "role": "donor"}
    with pytest.raises(HTTPException) as exc_info:
        get_current_donor({"id": "r1", "role": "receiver"})
    assert exc_info.value.status_code == 403


def test_auth_get_current_verified_receiver_guard():
    valid = {"id": "r1", "role": "receiver", "approval_status": "approved", "is_verified": True}
    assert get_current_verified_receiver(valid) == valid

    # Pending approval
    with pytest.raises(HTTPException) as exc1:
        get_current_verified_receiver({"id": "r1", "role": "receiver", "approval_status": "pending", "is_verified": False})
    assert exc1.value.status_code == 403

    # Wrong role
    with pytest.raises(HTTPException) as exc2:
        get_current_verified_receiver({"id": "d1", "role": "donor", "approval_status": "approved", "is_verified": True})
    assert exc2.value.status_code == 403


def test_auth_get_current_admin_guard():
    assert get_current_admin({"id": "a1", "role": "admin"}) == {"id": "a1", "role": "admin"}
    with pytest.raises(HTTPException) as exc_info:
        get_current_admin({"id": "d1", "role": "donor"})
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Section 3: Auth Endpoints (A-04, A-05)
# ---------------------------------------------------------------------------

def test_send_otp_success():
    req = SendOTPRequest(email="donor@example.com")
    mock_http_req = MagicMock()
    mock_http_req.client.host = "127.0.0.1"

    with patch("app.auth.routes.get_supabase") as mock_supabase, \
         patch("app.auth.routes.find_auth_user_by_email", return_value=None), \
         patch("app.auth.routes.auth_supabase") as mock_auth, \
         patch("app.auth.routes.enforce_otp_send_limit"):

        mock_supabase.return_value = MagicMock()
        mock_auth.auth.sign_in_with_otp.return_value = None

        res = send_otp(req, mock_http_req)

        assert "Verification code sent" in res["message"]
        assert res["is_new_user"] is True


def test_send_otp_supabase_failure():
    req = SendOTPRequest(email="donor@example.com")
    mock_http_req = MagicMock()
    mock_http_req.client.host = "127.0.0.1"
    with patch("app.auth.routes.auth_supabase") as mock_auth, \
         patch("app.auth.routes.enforce_otp_send_limit"):
        mock_auth.auth.sign_in_with_otp.side_effect = Exception("SMTP timeout")
        with pytest.raises(HTTPException) as exc_info:
            send_otp(req, mock_http_req)
        assert exc_info.value.status_code == 503


def test_verify_otp_existing_profile():
    req = VerifyOTPRequest(email="user@example.com", token="123456")
    mock_http_req = MagicMock()
    mock_http_req.client.host = "127.0.0.1"
    with patch("app.auth.routes.auth_supabase") as mock_auth, \
         patch("app.auth.routes.get_supabase") as mock_db, \
         patch("app.auth.routes.enforce_otp_send_limit"):
        mock_verification = MagicMock()
        mock_verification.user.id = "user-123"
        mock_verification.user.email = "user@example.com"
        mock_verification.session.access_token = "at-token"
        mock_verification.session.refresh_token = "rt-token"
        mock_verification.session.token_type = "bearer"
        mock_verification.session.expires_in = 3600
        mock_auth.auth.verify_otp.return_value = mock_verification

        mock_db.return_value.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "user-123", "full_name": "Alice", "role": "donor", "organization_name": None, "is_verified": False, "approval_status": None}
        ]

        res = verify_otp(req, mock_http_req)
        assert res["profile"]["full_name"] == "Alice"
        assert res["session"]["access_token"] == "at-token"


def test_verify_otp_new_profile_missing_role():
    req = VerifyOTPRequest(email="user@example.com", token="123456")
    mock_http_req = MagicMock()
    mock_http_req.client.host = "127.0.0.1"
    with patch("app.auth.routes.auth_supabase") as mock_auth, \
         patch("app.auth.routes.get_supabase") as mock_db, \
         patch("app.auth.routes.enforce_otp_send_limit"):
        mock_verification = MagicMock()
        mock_verification.user.id = "user-123"
        mock_verification.user.email = "user@example.com"
        mock_auth.auth.verify_otp.return_value = mock_verification

        # Profile does not exist
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

        with pytest.raises(HTTPException) as exc_info:
            verify_otp(req, mock_http_req)
        assert exc_info.value.status_code == 422
        assert "full_name and role are required" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Section 4: Food Listings Endpoints (A-06 to A-11, X-05)
# ---------------------------------------------------------------------------

def test_create_listing_success():
    future_time = datetime.now(timezone.utc) + timedelta(hours=4)
    data = FoodListingCreate(
        title="Surplus Rice",
        food_category="human",
        quantity="10 kg",
        pickup_address="123 Test Street",
        latitude=12.97,
        longitude=77.59,
        safe_until=future_time,
    )
    donor = {"id": "donor-uuid-1", "role": "donor"}
    with patch("app.listings.routes.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "list-uuid-1", "title": "Surplus Rice", "status": "available"}
        ]
        res = create_listing(data, donor=donor)
        assert res["listing"]["id"] == "list-uuid-1"
        assert res["message"] == "Food listing created successfully"


def test_get_available_listings_privacy():
    future_time = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    with patch("app.listings.routes.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.gt.return_value.order.return_value.range.return_value.execute.return_value.data = [
            {
                "id": "list-uuid-1",
                "title": "Fresh Fruits",
                "food_category": "human",
                "quantity": "5 kg",
                "safe_until": future_time,
                "status": "available",
                "created_at": "2026-11-14T00:00:00+00:00",
            }
        ]
        res = get_available_listings(category=None, limit=20, offset=0, latitude=None, longitude=None, radius_km=None)
        assert res["count"] == 1
        listing = res["listings"][0]
        assert "pickup_address" not in listing
        assert "latitude" not in listing
        assert "longitude" not in listing


def test_get_available_listings_radius_partial_params():
    with patch("app.listings.routes.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.gt.return_value.order.return_value.range.return_value.execute.return_value.data = []
        with pytest.raises(HTTPException) as exc_info:
            get_available_listings(category=None, limit=20, offset=0, latitude=12.97, longitude=None, radius_km=10.0)
        assert exc_info.value.status_code == 422


def test_get_my_listings_donor():
    donor = {"id": "donor-uuid-1", "role": "donor"}
    with patch("app.listings.routes.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "id": "list-1",
                "donor_id": "donor-uuid-1",
                "pickup_address": "Private Address 123",
                "latitude": 12.97,
                "longitude": 77.59,
            }
        ]
        res = get_my_listings(donor=donor)
        assert res["count"] == 1
        assert res["listings"][0]["pickup_address"] == "Private Address 123"


def test_get_listing_details_owner_sees_address():
    list_id = uuid.uuid4()
    future_time = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    user = {"id": "donor-uuid-1", "role": "donor"}
    with patch("app.listings.routes.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {
                "id": str(list_id),
                "donor_id": "donor-uuid-1",
                "title": "Meal Pack",
                "safe_until": future_time,
                "pickup_address": "Secret Pickup 123",
                "latitude": 12.97,
                "longitude": 77.59,
            }
        ]
        res = get_listing_details(list_id, current_user=user)
        assert "pickup_address" in res["listing"]
        assert "donor_id" not in res["listing"]  # donor_id is popped


def test_get_listing_details_verified_receiver_active_claim_sees_address():
    list_id = uuid.uuid4()
    future_time = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    claim_expiry = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    user = {"id": "recv-uuid-1", "role": "receiver", "is_verified": True, "approval_status": "approved"}
    with patch("app.listings.routes.get_supabase") as mock_db:
        mock_table = mock_db.return_value.table.return_value
        # Listing response
        mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {
                "id": str(list_id),
                "donor_id": "donor-uuid-1",
                "title": "Meal Pack",
                "safe_until": future_time,
                "pickup_address": "Secret Pickup 123",
                "latitude": 12.97,
                "longitude": 77.59,
            }
        ]
        # Claim check response
        mock_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {
                "id": "claim-1",
                "status": "active",
                "expires_at": claim_expiry,
            }
        ]
        res = get_listing_details(list_id, current_user=user)
        assert "pickup_address" in res["listing"]
        assert res["listing"]["pickup_address"] == "Secret Pickup 123"


def test_update_listing_empty_payload_rejected():
    list_id = uuid.uuid4()
    donor = {"id": "donor-uuid-1", "role": "donor"}
    changes = FoodListingUpdate()
    with pytest.raises(HTTPException) as exc_info:
        update_listing(list_id, changes, donor=donor)
    assert exc_info.value.status_code == 422


def test_update_listing_coords_must_be_together():
    with pytest.raises(ValidationError):
        FoodListingUpdate(latitude=12.97)


def test_get_listing_details_unauthorized_user_address_hidden():
    list_id = uuid.uuid4()
    future_time = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    # Different user (not owner, no claim)
    user = {"id": "stranger-uuid", "role": "receiver", "is_verified": False, "approval_status": "pending"}
    with patch("app.listings.routes.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {
                "id": str(list_id),
                "donor_id": "donor-uuid-1",
                "title": "Meal Pack",
                "safe_until": future_time,
                "pickup_address": "Secret Pickup 123",
                "latitude": 12.97,
                "longitude": 77.59,
            }
        ]
        res = get_listing_details(list_id, current_user=user)
        assert "pickup_address" not in res["listing"]
        assert "latitude" not in res["listing"]


def test_update_listing_rpc_conflict():
    list_id = uuid.uuid4()
    donor = {"id": "donor-uuid-1", "role": "donor"}
    changes = FoodListingUpdate(title="Updated Title")
    with patch("app.listings.routes.get_supabase") as mock_db:
        mock_db.return_value.rpc.return_value.execute.return_value.data = {
            "success": False,
            "code": "CONFLICT",
        }
        with pytest.raises(HTTPException) as exc_info:
            update_listing(list_id, changes, donor=donor)
        assert exc_info.value.status_code == 409


def test_cancel_listing_rpc_success():
    list_id = uuid.uuid4()
    donor = {"id": "donor-uuid-1", "role": "donor"}
    with patch("app.listings.routes.get_supabase") as mock_db:
        mock_db.return_value.rpc.return_value.execute.return_value.data = {
            "success": True,
            "listing_id": str(list_id),
            "status": "cancelled",
        }
        res = cancel_listing(list_id, donor=donor)
        assert res["result"]["status"] == "cancelled"


# ---------------------------------------------------------------------------
# Section 5: Claims Endpoints (A-12 to A-14, X-07)
# ---------------------------------------------------------------------------

def test_create_claim_success():
    list_id = uuid.uuid4()
    req = ClaimRequest(listing_id=list_id)
    user = {"id": "recv-uuid-1", "role": "receiver", "is_verified": True, "approval_status": "approved"}
    with patch("app.claims.routes.get_supabase") as mock_db:
        mock_db.return_value.rpc.return_value.execute.return_value.data = {
            "success": True,
            "claim_id": "claim-uuid-1",
            "listing_id": str(list_id),
            "status": "active",
        }
        res = create_claim(req, user=user)
        assert res["claim"]["claim_id"] == "claim-uuid-1"
        assert res["message"] == "Food listing claimed successfully"


def test_create_claim_conflict_already_claimed():
    list_id = uuid.uuid4()
    req = ClaimRequest(listing_id=list_id)
    user = {"id": "recv-uuid-1", "role": "receiver", "is_verified": True, "approval_status": "approved"}
    with patch("app.claims.routes.get_supabase") as mock_db:
        mock_db.return_value.rpc.return_value.execute.return_value.data = {
            "success": False,
            "code": "CONFLICT",
            "message": "Active claim already exists",
        }
        with pytest.raises(HTTPException) as exc_info:
            create_claim(req, user=user)
        assert exc_info.value.status_code == 409


def test_create_claim_expired_food():
    list_id = uuid.uuid4()
    req = ClaimRequest(listing_id=list_id)
    user = {"id": "recv-uuid-1", "role": "receiver", "is_verified": True, "approval_status": "approved"}
    with patch("app.claims.routes.get_supabase") as mock_db:
        mock_db.return_value.rpc.return_value.execute.return_value.data = {
            "success": False,
            "code": "EXPIRED",
            "message": "Listing expired",
        }
        with pytest.raises(HTTPException) as exc_info:
            create_claim(req, user=user)
        assert exc_info.value.status_code == 410


def test_cancel_claim_rpc_success():
    claim_id = uuid.uuid4()
    user = {"id": "recv-uuid-1", "role": "receiver", "is_verified": True, "approval_status": "approved"}
    with patch("app.claims.routes.get_supabase") as mock_db:
        mock_db.return_value.rpc.return_value.execute.return_value.data = {
            "success": True,
            "claim_status": "cancelled",
            "listing_status": "available",
        }
        res = cancel_claim(claim_id, user=user)
        assert res["result"]["claim_status"] == "cancelled"


def test_get_my_claims_privacy():
    user = {"id": "recv-uuid-1", "role": "receiver", "is_verified": True, "approval_status": "approved"}
    future_safe = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    active_expiry = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    expired_claim_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

    with patch("app.claims.routes.get_supabase") as mock_db:
        mock_client = mock_db.return_value

        claims_tbl = MagicMock()
        claims_tbl.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {
                "id": "c1",
                "listing_id": "l1",
                "status": "active",
                "claimed_at": "2026-11-14T00:00:00+00:00",
                "expires_at": active_expiry,
            },
            {
                "id": "c2",
                "listing_id": "l2",
                "status": "expired",
                "claimed_at": "2026-11-14T00:00:00+00:00",
                "expires_at": expired_claim_time,
            },
        ]

        def table_side_effect(name):
            if name == "claims":
                return claims_tbl
            mock_tbl = MagicMock()
            if name == "food_listings":
                def eq_side_effect(col, val):
                    mock_query = MagicMock()
                    if val == "l1":
                        mock_query.limit.return_value.execute.return_value.data = [
                            {
                                "id": "l1",
                                "title": "Pulao",
                                "safe_until": future_safe,
                                "pickup_address": "Visible Active Address",
                                "latitude": 12.97,
                                "longitude": 77.59,
                            }
                        ]
                    else:
                        mock_query.limit.return_value.execute.return_value.data = [
                            {
                                "id": "l2",
                                "title": "Dal",
                                "safe_until": future_safe,
                                "pickup_address": "Hidden Expired Address",
                                "latitude": 12.97,
                                "longitude": 77.59,
                            }
                        ]
                    return mock_query
                mock_tbl.select.return_value.eq.side_effect = eq_side_effect
            return mock_tbl

        mock_client.table.side_effect = table_side_effect

        res = get_my_claims(user=user)
        assert res["count"] == 2
        # c1 is active and food is safe: pickup_address is retained
        assert "pickup_address" in res["claims"][0]["listing"]
        assert res["claims"][0]["listing"]["pickup_address"] == "Visible Active Address"
        # c2 is expired: pickup_address and coords are stripped
        assert "pickup_address" not in res["claims"][1]["listing"]
        assert "latitude" not in res["claims"][1]["listing"]


# ---------------------------------------------------------------------------
# Section 6: Admin Endpoints (A-15 to A-18)
# ---------------------------------------------------------------------------

def test_admin_get_pending_receivers():
    admin = {"id": "admin-1", "role": "admin"}
    with patch("app.admin.routes.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {"id": "r1", "full_name": "Hope Shelter", "approval_status": "pending"}
        ]
        res = get_pending_receivers(_admin=admin)
        assert res["count"] == 1
        assert res["receivers"][0]["full_name"] == "Hope Shelter"


def test_admin_get_receiver_details_not_found():
    admin = {"id": "admin-1", "role": "admin"}
    recv_id = uuid.uuid4()
    with patch("app.admin.routes.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        with pytest.raises(HTTPException) as exc_info:
            get_receiver_details(recv_id, _admin=admin)
        assert exc_info.value.status_code == 404


def test_admin_approve_receiver_success():
    admin = {"id": "admin-1", "role": "admin"}
    recv_id = uuid.uuid4()
    with patch("app.admin.routes.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.select.return_value.execute.return_value.data = [
            {"id": str(recv_id), "approval_status": "approved", "is_verified": True}
        ]
        res = approve_receiver(recv_id, _admin=admin)
        assert res["receiver"]["approval_status"] == "approved"
        assert res["receiver"]["is_verified"] is True


def test_admin_approve_receiver_conflict():
    admin = {"id": "admin-1", "role": "admin"}
    recv_id = uuid.uuid4()
    with patch("app.admin.routes.get_supabase") as mock_db:
        # Update returns 0 rows
        mock_db.return_value.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.select.return_value.execute.return_value.data = []
        # Check existing returns empty (not pending)
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        with pytest.raises(HTTPException) as exc_info:
            approve_receiver(recv_id, _admin=admin)
        assert exc_info.value.status_code == 409


def test_admin_reject_receiver_success():
    admin = {"id": "admin-1", "role": "admin"}
    recv_id = uuid.uuid4()
    with patch("app.admin.routes.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.select.return_value.execute.return_value.data = [
            {"id": str(recv_id), "approval_status": "rejected", "is_verified": False}
        ]
        res = reject_receiver(recv_id, _admin=admin)
        assert res["receiver"]["approval_status"] == "rejected"
        assert res["receiver"]["is_verified"] is False


# ---------------------------------------------------------------------------
# Section 7: Operations and Lifespan (A-01, A-02, A-03)
# ---------------------------------------------------------------------------

def test_root_endpoint():
    res = root()
    assert res["status"] == "running"
    assert "version" in res


def test_health_endpoint_healthy():
    with patch("app.main.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock()
        res = health()
        assert res["status"] == "healthy"
        assert res["database"] == "connected"


def test_health_endpoint_db_down():
    with patch("app.main.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.select.return_value.limit.return_value.execute.side_effect = Exception("DB unreachable")
        with pytest.raises(HTTPException) as exc_info:
            health()
        assert exc_info.value.status_code == 503


def test_trigger_expiry_sweep_endpoint():
    admin = {"id": "admin-1", "role": "admin"}
    with patch("app.main.run_expiry_and_timeout_sweep") as mock_sweep:
        mock_sweep.return_value = {"expired_claims": 2, "reopened_listings": 1, "expired_listings": 0}
        res = trigger_expiry_sweep(_admin=admin)
        assert res["results"]["expired_claims"] == 2
