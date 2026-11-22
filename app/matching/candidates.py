"""Receiver location rules and matching candidates (Member 2). Pure functions.

Receiver coordinates live in the separate receiver_locations table
(receiver_id, latitude, longitude, updated_at). A receiver without a valid
location is simply excluded from distance-based matching.
Precise receiver coordinates are private: they are only ever returned to the
receiver who owns them, never in donor-facing or public listing responses.
"""
import math
from typing import Any, Dict, List, Optional, Tuple

OK = "ok"
MISSING_COORDINATES = "missing_coordinates"
INVALID_COORDINATES = "invalid_coordinates"
OUT_OF_RANGE = "out_of_range"
NOT_RECEIVER = "not_receiver"
NOT_APPROVED = "not_approved"

LATITUDE_LIMIT = 90.0
LONGITUDE_LIMIT = 180.0
DECIMALS = 6   # matches NUMERIC(9,6)


def _number(value: Any, allow_strings: bool) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif allow_strings and isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def validate_location(
    latitude: Any, longitude: Any
) -> Tuple[Optional[Dict[str, float]], str]:
    """Strict check for coordinates sent by a client. Both are required."""
    if latitude is None or longitude is None:
        return None, MISSING_COORDINATES
    lat = _number(latitude, allow_strings=False)
    lng = _number(longitude, allow_strings=False)
    if lat is None or lng is None:
        return None, INVALID_COORDINATES
    if abs(lat) > LATITUDE_LIMIT or abs(lng) > LONGITUDE_LIMIT:
        return None, OUT_OF_RANGE
    return {"latitude": round(lat, DECIMALS), "longitude": round(lng, DECIMALS)}, OK


def check_location_authorization(profile: Optional[Dict[str, Any]]) -> str:
    """Only an approved, verified receiver may save a location."""
    if not profile or profile.get("role") != "receiver":
        return NOT_RECEIVER
    if profile.get("approval_status") != "approved" or not profile.get("is_verified"):
        return NOT_APPROVED
    return OK


def _embedded_location(profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    embedded = profile.get("receiver_locations")
    if isinstance(embedded, dict):
        return embedded
    if isinstance(embedded, list) and embedded:
        return embedded[0] if isinstance(embedded[0], dict) else None
    return None


def build_candidates(
    profiles: List[Dict[str, Any]],
    locations: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Join profiles with receiver_locations for match_receivers().

    Receivers with no location, or a stored location that is invalid, are
    dropped. Approval, verification, flag and category checks stay in
    match_receivers(). Inputs are never modified.
    """
    by_receiver = {row.get("receiver_id"): row for row in (locations or [])}
    candidates: List[Dict[str, Any]] = []
    for profile in profiles:
        if profile.get("role") != "receiver":
            continue
        location = by_receiver.get(profile.get("id")) or _embedded_location(profile)
        if not location:
            continue
        lat = _number(location.get("latitude"), allow_strings=True)
        lng = _number(location.get("longitude"), allow_strings=True)
        if lat is None or lng is None:
            continue
        if abs(lat) > LATITUDE_LIMIT or abs(lng) > LONGITUDE_LIMIT:
            continue
        candidate = {k: v for k, v in profile.items() if k != "receiver_locations"}
        candidate["latitude"] = lat
        candidate["longitude"] = lng
        candidates.append(candidate)
    return candidates
