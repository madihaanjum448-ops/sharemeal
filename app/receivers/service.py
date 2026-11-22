"""Receiver location save/read logic (Member 2). No FastAPI imports.

The receiver id ALWAYS comes from the authenticated user, never from the
request body. Coordinates are private: they are returned only to their owner.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.matching.candidates import (
    INVALID_COORDINATES,
    OK,
    check_location_authorization,
    validate_location,
)

logger = logging.getLogger(__name__)

TABLE = "receiver_locations"
LOCATION_NOT_SET = "location_not_set"
SERVICE_UNAVAILABLE = "location_service_unavailable"


class LocationError(Exception):
    """Carries the HTTP status and the short error code for the response."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _require_approved_receiver(user: Optional[Dict[str, Any]]) -> None:
    status = check_location_authorization(user)
    if status != OK:
        raise LocationError(403, status)


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def save_location(
    client: Any,
    user: Dict[str, Any],
    payload: Any,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Create or update the logged-in receiver's location (idempotent)."""
    _require_approved_receiver(user)
    if not isinstance(payload, dict):
        raise LocationError(422, INVALID_COORDINATES)
    clean, status = validate_location(payload.get("latitude"), payload.get("longitude"))
    if clean is None:
        raise LocationError(422, status)

    moment = now or datetime.now(timezone.utc)
    updated_at = moment.isoformat().replace("+00:00", "Z")
    row = {
        "receiver_id": user["id"],          # from the token, never from the body
        "latitude": clean["latitude"],
        "longitude": clean["longitude"],
        "updated_at": updated_at,
    }
    try:
        client.table(TABLE).upsert(row, on_conflict="receiver_id").execute()
    except Exception as exc:                 # noqa: BLE001
        logger.error("receiver location save failed: %s", type(exc).__name__)
        raise LocationError(503, SERVICE_UNAVAILABLE)

    return {
        "latitude": clean["latitude"],
        "longitude": clean["longitude"],
        "updated_at": updated_at,
    }


def read_location(client: Any, user: Dict[str, Any]) -> Dict[str, Any]:
    """Return the logged-in receiver's own saved location."""
    _require_approved_receiver(user)
    try:
        result = (
            client.table(TABLE)
            .select("latitude, longitude, updated_at")
            .eq("receiver_id", user["id"])
            .limit(1)
            .execute()
        )
    except Exception as exc:                 # noqa: BLE001
        logger.error("receiver location read failed: %s", type(exc).__name__)
        raise LocationError(503, SERVICE_UNAVAILABLE)

    rows = result.data or []
    if not rows:
        raise LocationError(404, LOCATION_NOT_SET)
    row = rows[0]
    clean, _ = validate_location(_to_float(row.get("latitude")), _to_float(row.get("longitude")))
    if clean is None:
        raise LocationError(404, LOCATION_NOT_SET)
    return {
        "latitude": clean["latitude"],
        "longitude": clean["longitude"],
        "updated_at": row.get("updated_at"),
    }
