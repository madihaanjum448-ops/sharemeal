"""Alert delivery (Member 2). Pure logic; the real senders are injected.

Rules from the PRD:
- A notification failure NEVER raises and NEVER touches claim or listing state.
- Alerts never contain the exact pickup address or coordinates.
- Channels are tried in order (web push first, Telegram as fallback).
- Failures are recorded by exception TYPE only, so no token or URL is logged.
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

MAX_DELIVERY_ATTEMPTS = 3          # placeholder, pending team sign-off
DEFAULT_LISTING_PATH = "/receiver/listings"   # confirm with Member 4's routes
MAX_BODY_LENGTH = 120

# A sender takes (receiver, payload) and returns True only if it delivered.
Sender = Callable[[Dict[str, Any], Dict[str, Any]], bool]
Channel = Tuple[str, Sender]


@dataclass(frozen=True)
class DeliveryResult:
    receiver_id: str
    delivered: bool
    channel: Optional[str] = None
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class DispatchOutcome:
    delivered_ids: List[str]
    attempts: Dict[str, int]
    results: List[DeliveryResult] = field(default_factory=list)


def listing_deep_link(listing_id: Any, base_path: str = DEFAULT_LISTING_PATH) -> str:
    return "%s/%s" % (base_path.rstrip("/"), listing_id)


def build_alert_payload(
    listing: Dict[str, Any], base_path: str = DEFAULT_LISTING_PATH
) -> Dict[str, Any]:
    """Public-safe payload: no pickup address, no exact coordinates."""
    parts: List[str] = []
    if listing.get("title"):
        parts.append(str(listing["title"]))
    if listing.get("servings"):
        parts.append("%s servings" % listing["servings"])
    category = listing.get("food_category")
    if category == "human":
        parts.append("for people")
    elif category == "animal":
        parts.append("for animals")
    body = " | ".join(parts) or "New food listing nearby"
    if len(body) > MAX_BODY_LENGTH:
        body = body[: MAX_BODY_LENGTH - 3] + "..."
    return {
        "title": "Food available near you",
        "body": body,
        "url": listing_deep_link(listing["id"], base_path),
        "listing_id": listing["id"],
        "tag": "listing-%s" % listing["id"],   # collapses duplicate alerts on one device
    }


def deliver_to_receiver(
    receiver: Dict[str, Any],
    payload: Dict[str, Any],
    channels: Sequence[Channel],
) -> DeliveryResult:
    """Try each channel in order. Never raises."""
    errors: List[str] = []
    for name, sender in channels:
        try:
            if sender(receiver, payload):
                return DeliveryResult(receiver.get("id"), True, name, tuple(errors))
            errors.append("%s: not delivered" % name)
        except Exception as exc:                      # noqa: BLE001 - must never escape
            errors.append("%s: %s" % (name, type(exc).__name__))
    return DeliveryResult(receiver.get("id"), False, None, tuple(errors))


def dispatch_alerts(
    listing: Dict[str, Any],
    receivers: List[Dict[str, Any]],
    channels: Sequence[Channel],
    attempts: Optional[Dict[str, int]] = None,
    max_attempts: int = MAX_DELIVERY_ATTEMPTS,
) -> DispatchOutcome:
    """Alert each receiver. Returns who was reached and updated attempt counts.

    Only receivers actually reached are returned in delivered_ids, so only
    those should be recorded as alerted. A failed receiver stays eligible and
    is retried on the next run until max_attempts is reached.
    The input attempts dict is never modified.
    """
    new_attempts = dict(attempts or {})
    payload = build_alert_payload(listing)
    delivered: List[str] = []
    results: List[DeliveryResult] = []

    for receiver in receivers:
        rid = receiver.get("id")
        if new_attempts.get(rid, 0) >= max_attempts:
            continue                                  # gave up on this receiver
        result = deliver_to_receiver(receiver, payload, channels)
        results.append(result)
        if result.delivered:
            delivered.append(rid)
        else:
            new_attempts[rid] = new_attempts.get(rid, 0) + 1

    return DispatchOutcome(delivered, new_attempts, results)
