"""Load matching candidates from the database (Member 2).

Profiles and receiver_locations are fetched separately and joined in Python,
so this does not depend on any database join syntax. Receivers without a
saved location are left out of distance-based matching.

The "flagged" status is derived from strike_events (3 timeout strikes since the
latest admin_clear), so it never depends on a user_profiles.is_flagged column.
"""
import logging
from typing import Any, Dict, List, Set

from app.matching.candidates import build_candidates
from app.strikes.service import StrikeEvent, is_flagged

logger = logging.getLogger("sharemeal.matching")

PROFILE_COLUMNS = "id, role, approval_status, is_verified, accepts_food_category"
LOCATION_COLUMNS = "receiver_id, latitude, longitude"
STRIKE_COLUMNS = "receiver_id, claim_id, event_type, reason, created_at"


def fetch_flagged_receiver_ids(client: Any) -> Set[str]:
    """Receivers with 3+ timeout strikes since their latest admin clear. Never raises."""
    try:
        rows = (
            client.table("strike_events")
            .select(STRIKE_COLUMNS)
            .in_("event_type", ["timeout", "admin_clear"])
            .order("created_at")
            .execute()
            .data
            or []
        )
        events = [
            StrikeEvent(
                str(r["receiver_id"]), str(r.get("claim_id") or ""),
                r["event_type"], r.get("reason") or "", r["created_at"],
            )
            for r in rows
        ]
    except Exception as exc:                          # noqa: BLE001
        logger.error("strike lookup failed: %s", type(exc).__name__)
        return set()
    return {rid for rid in {e.receiver_id for e in events} if is_flagged(events, rid)}


def fetch_matching_candidates(client: Any) -> List[Dict[str, Any]]:
    profiles = (
        client.table("user_profiles")
        .select(PROFILE_COLUMNS)
        .eq("role", "receiver")
        .execute()
        .data
        or []
    )
    locations = client.table("receiver_locations").select(LOCATION_COLUMNS).execute().data or []
    candidates = build_candidates(profiles, locations)
    flagged = fetch_flagged_receiver_ids(client)
    for candidate in candidates:
        candidate["is_flagged"] = str(candidate.get("id")) in flagged
    return candidates
