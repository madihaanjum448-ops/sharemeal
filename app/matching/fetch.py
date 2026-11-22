"""Load matching candidates from the database (Member 2).

Profiles and receiver_locations are fetched separately and joined in Python,
so this does not depend on any database join syntax. Receivers without a
saved location are left out of distance-based matching.
"""
from typing import Any, Dict, List

from app.matching.candidates import build_candidates

PROFILE_COLUMNS = "id, role, approval_status, is_verified, is_flagged, accepts_food_category"
LOCATION_COLUMNS = "receiver_id, latitude, longitude"


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
    return build_candidates(profiles, locations)
