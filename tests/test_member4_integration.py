import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.auth.schemas import RefreshTokenRequest
from app.auth.routes import get_current_user_profile, refresh_token
from app.listings.routes import get_available_listings
from app.claims.routes import ClaimRequest, create_claim
from app.main import app


# ---------------------------------------------------------------------------
# Task A: Public Listing Feed Map Fields & Privacy (approx coords, distance)
# ---------------------------------------------------------------------------

def test_listings_feed_approx_coords_and_distance():
    """Verify that GET /listings/ returns approx_latitude, approx_longitude, and distance_km when user coordinates and radius are provided."""
    future_time = (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()
    # Exact coordinates for Indiranagar listing: 12.978432, 77.640821
    with patch("app.listings.routes.get_supabase") as mock_db:
        mock_table = mock_db.return_value.table.return_value
        sample_data = [
            {
                "id": "list-1",
                "title": "Vegetable Biryani",
                "food_category": "human",
                "quantity": "10 packs",
                "servings": 10,
                "safe_until": future_time,
                "status": "available",
                "created_at": "2026-11-14T10:00:00+00:00",
                "pickup_address": "142, 100ft Road, Indiranagar",
                "latitude": 12.978432,
                "longitude": 77.640821,
            }
        ]
        mock_table.select.return_value.eq.return_value.gt.return_value.limit.return_value.execute.return_value.data = sample_data
        mock_table.select.return_value.eq.return_value.gt.return_value.order.return_value.range.return_value.execute.return_value.data = sample_data

        # User searches from Koramangala (lat 12.9352, lng 77.6245) with radius_km=10
        res = get_available_listings(
            category=None,
            food_category=None,
            limit=20,
            offset=0,
            latitude=12.9352,
            lat=None,
            longitude=77.6245,
            lng=None,
            radius_km=10.0,
        )

        assert res["count"] == 1
        item = res["listings"][0]

        # Verify approximate coordinates (rounded to 2 decimal places ~1.1 km resolution)
        assert item["approx_latitude"] == 12.98
        assert item["approx_longitude"] == 77.64

        # Verify distance_km is computed (~5.1 km between Indiranagar and Koramangala)
        assert item["distance_km"] is not None
        assert 4.0 <= item["distance_km"] <= 6.5

        # STRICT PRIVACY: Verify exact coordinates and address are NEVER returned
        assert "pickup_address" not in item
        assert "latitude" not in item
        assert "longitude" not in item
        assert "donor_id" not in item


def test_listings_feed_no_user_coords_distance_is_none():
    """Verify that when no user coordinates are provided, distance_km is None and approx coords are present."""
    future_time = (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()
    with patch("app.listings.routes.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.gt.return_value.order.return_value.range.return_value.execute.return_value.data = [
            {
                "id": "list-2",
                "title": "Bakery Breads",
                "food_category": "human",
                "quantity": "5 loaves",
                "safe_until": future_time,
                "status": "available",
                "created_at": "2026-11-14T10:00:00+00:00",
                "latitude": 12.9866,
                "longitude": 77.7381,
            }
        ]

        res = get_available_listings(
            category=None,
            food_category=None,
            limit=20,
            offset=0,
            latitude=None,
            lat=None,
            longitude=None,
            lng=None,
            radius_km=None,
        )

        assert res["count"] == 1
        item = res["listings"][0]
        assert item["approx_latitude"] == 12.99
        assert item["approx_longitude"] == 77.74
        assert item["distance_km"] is None
        assert "pickup_address" not in item
        assert "latitude" not in item
        assert "longitude" not in item


def test_listings_feed_accepts_member4_aliases():
    """Verify that food_category, lat, and lng aliases work identically."""
    future_time = (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()
    with patch("app.listings.routes.get_supabase") as mock_db:
        mock_table = mock_db.return_value.table.return_value
        sample_data = [
            {
                "id": "list-3",
                "title": "Dog Food Broth",
                "food_category": "animal",
                "quantity": "10 kg",
                "safe_until": future_time,
                "status": "available",
                "created_at": "2026-11-14T10:00:00+00:00",
                "latitude": 12.9352,
                "longitude": 77.6245,
            }
        ]
        mock_table.select.return_value.eq.return_value.gt.return_value.limit.return_value.execute.return_value.data = sample_data
        mock_table.select.return_value.eq.return_value.gt.return_value.order.return_value.range.return_value.execute.return_value.data = sample_data

        # Use member 4 alias parameters: food_category, lat, lng, radius_km
        res = get_available_listings(
            category=None,
            food_category="animal",
            limit=10,
            offset=0,
            latitude=None,
            lat=12.9352,
            longitude=None,
            lng=77.6245,
            radius_km=10.0,
        )

        assert res["count"] == 1
        item = res["listings"][0]
        assert item["approx_latitude"] == 12.94
        assert item["approx_longitude"] == 77.62
        assert item["distance_km"] == 0.0  # same coordinates


# ---------------------------------------------------------------------------
# Task B: Current Authenticated User (GET /auth/me)
# ---------------------------------------------------------------------------

def test_auth_me_authenticated_success():
    """Verify GET /auth/me returns complete authenticated profile."""
    current_user = {
        "id": "r0000001-0000-0000-0000-000000000001",
        "email": "receiver@example.com",
        "role": "receiver",
        "is_verified": True,
        "approval_status": "approved",
    }
    with patch("app.auth.routes.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {
                "id": "r0000001-0000-0000-0000-000000000001",
                "full_name": "Sneha Care Foundation",
                "phone": "+919876500010",
                "role": "receiver",
                "organization_name": "Sneha Child & Care Society",
                "is_verified": True,
                "approval_status": "approved",
                "created_at": "2026-11-10T10:00:00+00:00",
            }
        ]

        res = get_current_user_profile(user=current_user)
        assert res["id"] == "r0000001-0000-0000-0000-000000000001"
        assert res["email"] == "receiver@example.com"
        assert res["full_name"] == "Sneha Care Foundation"
        assert res["role"] == "receiver"
        assert res["organization_name"] == "Sneha Child & Care Society"
        assert res["is_verified"] is True
        assert res["approval_status"] == "approved"
        # Verify backward-compatible nested user object is also present
        assert res["user"]["id"] == "r0000001-0000-0000-0000-000000000001"


def test_auth_me_profile_not_found():
    """Verify GET /auth/me raises 404 if profile row is missing."""
    current_user = {"id": "missing-uuid", "email": "test@example.com"}
    with patch("app.auth.routes.get_supabase") as mock_db:
        mock_db.return_value.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
        with pytest.raises(HTTPException) as exc_info:
            get_current_user_profile(user=current_user)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Task C: Session Token Refresh (POST /auth/refresh)
# ---------------------------------------------------------------------------

def test_auth_refresh_token_success():
    """Verify POST /auth/refresh returns new session tokens."""
    req = RefreshTokenRequest(refresh_token="valid-refresh-token-12345")
    mock_refresh_res = MagicMock()
    mock_session = MagicMock()
    mock_session.access_token = "new-access-token-67890"
    mock_session.refresh_token = "new-refresh-token-67890"
    mock_session.token_type = "bearer"
    mock_session.expires_in = 3600
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_user.email = "user@example.com"
    mock_refresh_res.session = mock_session
    mock_refresh_res.user = mock_user

    with patch("app.auth.routes.auth_supabase") as mock_auth:
        mock_auth.auth.refresh_session.return_value = mock_refresh_res
        res = refresh_token(req)

        assert res["message"] == "Token refreshed successfully"
        assert res["access_token"] == "new-access-token-67890"
        assert res["refresh_token"] == "new-refresh-token-67890"
        assert res["expires_in"] == 3600
        assert res["user"]["email"] == "user@example.com"
        assert "session" not in res
        mock_auth.auth.refresh_session.assert_called_once_with("valid-refresh-token-12345")


def test_auth_refresh_token_invalid_or_expired():
    """Verify POST /auth/refresh raises 401 when token is invalid or expired."""
    req = RefreshTokenRequest(refresh_token="expired-token")
    with patch("app.auth.routes.auth_supabase") as mock_auth:
        mock_auth.auth.refresh_session.side_effect = Exception("Invalid Refresh Token: Already Used")
        with pytest.raises(HTTPException) as exc_info:
            refresh_token(req)
        assert exc_info.value.status_code == 401
        assert "Invalid or expired refresh token" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Task D: CORS Middleware Configuration
# ---------------------------------------------------------------------------

def test_cors_middleware_configured_for_member4():
    """Verify that app middleware contains CORSMiddleware configured for Member 4 origin."""
    cors_middlewares = [m for m in app.user_middleware if m.cls == CORSMiddleware]
    assert len(cors_middlewares) >= 1, "CORSMiddleware is not registered on FastAPI app"
    
    cors_kwargs = cors_middlewares[0].kwargs
    allow_origins = cors_kwargs.get("allow_origins", [])
    
    assert "http://localhost:5173" in allow_origins, "Member 4 frontend origin http://localhost:5173 missing from allowed origins"
    assert cors_kwargs.get("allow_credentials") is True
    # Ensure wildcard is not combined with credentials
    assert "*" not in allow_origins


# ---------------------------------------------------------------------------
# Task E: Claims Compatibility (/claims/create endpoint alias)
# ---------------------------------------------------------------------------

def test_claims_create_endpoint_alias():
    """Verify that POST /claims/create alias works identically to POST /claims/."""
    list_id = uuid.uuid4()
    req = ClaimRequest(listing_id=list_id)
    user = {"id": "recv-uuid-1", "role": "receiver", "is_verified": True, "approval_status": "approved"}
    with patch("app.claims.routes.get_supabase") as mock_db:
        mock_db.return_value.rpc.return_value.execute.return_value.data = {
            "success": True,
            "claim_id": "claim-uuid-999",
            "listing_id": str(list_id),
            "status": "active",
        }
        res = create_claim(req, user=user)
        assert res["claim"]["claim_id"] == "claim-uuid-999"
        assert res["message"] == "Food listing claimed successfully"
