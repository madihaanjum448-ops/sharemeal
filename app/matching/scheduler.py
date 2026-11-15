"""Alert planning for the matching scheduler (Member 2). Pure functions.

Given a listing and the receivers already alerted, return only the receivers
that should be alerted NOW. Calling it again with the same inputs returns
nothing new, so a retried job cannot send duplicate alerts.
"""
from datetime import datetime
from typing import Any, Dict, Iterable, List

from app.matching.matching import match_receivers


def minutes_since(created_at: datetime, now: datetime) -> float:
    return max(0.0, (now - created_at).total_seconds() / 60.0)


def plan_alerts(
    listing: Dict[str, Any],
    receivers: List[Dict[str, Any]],
    already_notified: Iterable[str],
    now: datetime,
) -> List[Dict[str, Any]]:
    """Return receivers to alert now, nearest first."""
    if listing.get("status") != "available":
        return []
    safe_until = listing.get("safe_until")
    if safe_until is not None and now >= safe_until:
        return []

    notified = set(already_notified)
    elapsed = minutes_since(listing["created_at"], now)
    matched = match_receivers(listing, receivers, elapsed)
    return [r for r in matched if r.get("id") not in notified]
