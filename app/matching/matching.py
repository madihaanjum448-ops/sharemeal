"""Tiered receiver matching (Member 2).

Pure functions, no database access. All distances and timings are
UNVALIDATED PLACEHOLDERS, not food-safety rules.
"""
from typing import Any, Dict, List, Optional, Tuple

from app.listings.geo import distance_km

# (minutes_elapsed_at_least, max_distance_km or None, max_receivers or None)
MATCHING_TIERS: List[Tuple[int, Optional[float], Optional[int]]] = [
    (0, 3.0, 5),
    (5, 8.0, None),
    (10, None, None),
]


def _category_fits(listing_category: Any, receiver_category: Any) -> bool:
    return receiver_category in (listing_category, "both")


def _is_eligible(listing: Dict[str, Any], receiver: Dict[str, Any]) -> bool:
    return (
        receiver.get("approval_status") == "approved"
        and bool(receiver.get("is_verified"))
        and not receiver.get("is_flagged", False)
        and _category_fits(
            listing.get("food_category"), receiver.get("accepts_food_category")
        )
    )


def _current_tier(minutes_elapsed: float) -> Tuple[int, Optional[float], Optional[int]]:
    tier = MATCHING_TIERS[0]
    for candidate in MATCHING_TIERS:
        if minutes_elapsed >= candidate[0]:
            tier = candidate
    return tier


def match_receivers(
    listing: Dict[str, Any],
    receivers: List[Dict[str, Any]],
    minutes_elapsed: float,
) -> List[Dict[str, Any]]:
    """Return receivers to alert, nearest first. Inputs are never modified."""
    _, max_km, max_count = _current_tier(minutes_elapsed)

    ranked = []
    for receiver in receivers:
        if not _is_eligible(listing, receiver):
            continue
        try:
            dist = distance_km(
                listing["latitude"],
                listing["longitude"],
                receiver["latitude"],
                receiver["longitude"],
            )
        except (KeyError, TypeError, ValueError):
            continue  # malformed coordinates: skip this receiver
        ranked.append((dist, receiver))

    ranked.sort(key=lambda pair: pair[0])

    if max_km is not None:
        ranked = [pair for pair in ranked if pair[0] <= max_km]
    if max_count is not None:
        ranked = ranked[:max_count]

    return [receiver for _, receiver in ranked]
