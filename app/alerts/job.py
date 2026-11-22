"""Alert job (Member 2): run matching for every available listing and record alerts.

Runs once per expiry-sweep cycle. It never raises, so it can never stop the sweep,
and it never changes claim or listing state.
"""
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from app.matching.fetch import fetch_matching_candidates
from app.matching.scheduler import plan_alerts
from app.notifications.service import Channel, dispatch_alerts
from app.notifications.telegram import build_channels

logger = logging.getLogger("sharemeal.alerts")


def parse_time(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip().replace("Z", "+00:00")
        text = re.sub(r"\.(\d+)", lambda m: "." + m.group(1)[:6].ljust(6, "0"), text)
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
    else:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def prepare_listing(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Turn a database row into what plan_alerts expects. None if unusable."""
    listing = dict(row)
    listing["created_at"] = parse_time(row.get("created_at"))
    listing["safe_until"] = parse_time(row.get("safe_until"))
    try:
        listing["latitude"] = float(row["latitude"])
        listing["longitude"] = float(row["longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    if listing["created_at"] is None or listing["safe_until"] is None:
        return None
    return listing


def _load_state(client: Any, listing_ids: List[str]):
    notified: Dict[str, set] = {}
    attempts: Dict[str, Dict[str, int]] = {}
    delivered_rows = (
        client.table("alert_deliveries").select("listing_id, receiver_id")
        .in_("listing_id", listing_ids).execute().data or []
    )
    for row in delivered_rows:
        notified.setdefault(str(row["listing_id"]), set()).add(str(row["receiver_id"]))
    attempt_rows = (
        client.table("alert_attempts").select("listing_id, receiver_id, attempts")
        .in_("listing_id", listing_ids).execute().data or []
    )
    for row in attempt_rows:
        attempts.setdefault(str(row["listing_id"]), {})[str(row["receiver_id"])] = int(row["attempts"])
    return notified, attempts


def run_alert_cycle(
    client: Any,
    now: Optional[datetime] = None,
    channels: Optional[Sequence[Channel]] = None,
    candidates: Optional[List[Dict[str, Any]]] = None,
) -> int:
    """Alert receivers for all available listings. Returns how many alerts were recorded."""
    try:
        now = now or datetime.now(timezone.utc)
        rows = client.table("food_listings").select("*").eq("status", "available").execute().data or []
        listings = [item for item in (prepare_listing(r) for r in rows) if item]
        if not listings:
            return 0
        if candidates is None:
            candidates = fetch_matching_candidates(client)
        if channels is None:
            channels = build_channels(client)
        ids = [str(item["id"]) for item in listings]
        notified, attempts = _load_state(client, ids)
    except Exception as exc:                       # noqa: BLE001
        logger.error("alert cycle setup failed: %s", type(exc).__name__)
        return 0

    total = 0
    for listing in listings:
        lid = str(listing["id"])
        try:
            to_alert = plan_alerts(listing, candidates, notified.get(lid, set()), now)
            if not to_alert:
                continue
            outcome = dispatch_alerts(listing, to_alert, channels, attempts.get(lid, {}))
            delivered_rows = [
                {"listing_id": lid, "receiver_id": str(r.receiver_id), "channel": r.channel}
                for r in outcome.results if r.delivered
            ]
            if delivered_rows:
                client.table("alert_deliveries").upsert(
                    delivered_rows, on_conflict="listing_id,receiver_id").execute()
                total += len(delivered_rows)
            failed_rows = [
                {"listing_id": lid, "receiver_id": str(rid), "attempts": count}
                for rid, count in outcome.attempts.items()
                if count != attempts.get(lid, {}).get(rid, 0)
            ]
            if failed_rows:
                client.table("alert_attempts").upsert(
                    failed_rows, on_conflict="listing_id,receiver_id").execute()
        except Exception as exc:                   # noqa: BLE001
            logger.error("alert cycle failed for one listing: %s", type(exc).__name__)
    if total:
        logger.info("alerts recorded: %s", total)
    return total
