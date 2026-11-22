"""Pickup handshake: database-facing logic (Member 2). No FastAPI imports.

Only a keyed hash of the code is stored. The plain code is recomputed from the
server secret for the donor, and is never logged or returned to the receiver.
"""
import logging
import os
import re
import uuid
from typing import Any, Dict, Optional

from app.handshake.service import derive_code, hash_code

logger = logging.getLogger(__name__)

MIN_SECRET_LENGTH = 16
CODE_PATTERN = re.compile(r"^[0-9]{4}$")

# result of the confirm_claim_pickup SQL function -> (HTTP status, error code)
RESULT_ERRORS = {
    "wrong_code": (400, "wrong_code"),
    "locked": (423, "locked"),
    "expired": (410, "expired"),
    "already_used": (409, "already_used"),
    "claim_not_active": (409, "claim_not_active"),
    "no_handshake": (409, "no_handshake"),
    "not_found": (404, "not_found"),
}


class HandshakeError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def get_secret() -> Optional[str]:
    """The server secret, or None when it is missing or too short."""
    secret = os.getenv("HANDSHAKE_SECRET", "").strip()
    return secret if len(secret) >= MIN_SECRET_LENGTH else None


def normalize_claim_id(claim_id: Any) -> Optional[str]:
    try:
        return str(uuid.UUID(str(claim_id)))
    except (ValueError, AttributeError, TypeError):
        return None


def start_handshake_for_claim(client: Any, claim_id: Any) -> bool:
    """Store the hashed code for a new claim. True when the claim may go ahead.

    If HANDSHAKE_SECRET is not configured the handshake is skipped (with a
    warning) so the claim flow itself keeps working.
    """
    secret = get_secret()
    if secret is None:
        logger.warning("HANDSHAKE_SECRET missing or too short: pickup handshake skipped")
        return True
    cid = normalize_claim_id(claim_id)
    if cid is None:
        return False
    code_hash = hash_code(derive_code(cid, secret), cid, secret)
    try:
        result = client.rpc(
            "start_claim_handshake", {"p_claim_id": cid, "p_code_hash": code_hash}
        ).execute()
    except Exception as exc:                 # noqa: BLE001
        logger.error("start_claim_handshake failed: %s", type(exc).__name__)
        return False
    return result.data is not None


def start_handshake_or_cancel(client: Any, claim_id: Any, receiver_id: Any) -> bool:
    """Start the handshake; if that fails, cancel the new claim. Never raises."""
    if start_handshake_for_claim(client, claim_id):
        return True
    cid = normalize_claim_id(claim_id)
    if cid is not None:
        try:
            client.rpc(
                "cancel_food_claim", {"p_claim_id": cid, "p_receiver_id": str(receiver_id)}
            ).execute()
        except Exception as exc:             # noqa: BLE001
            logger.error("claim cancel after handshake failure failed: %s", type(exc).__name__)
    return False


def confirm_pickup(client: Any, claim_id: Any, user: Dict[str, Any], code: Any) -> Dict[str, Any]:
    """Check the code the receiver typed. The actor is the logged-in user."""
    secret = get_secret()
    if secret is None:
        raise HandshakeError(503, "handshake_not_configured")
    if not isinstance(code, str) or not CODE_PATTERN.fullmatch(code):
        raise HandshakeError(422, "invalid_code_format")      # never reaches the database
    cid = normalize_claim_id(claim_id)
    if cid is None:
        raise HandshakeError(404, "not_found")
    try:
        result = client.rpc(
            "confirm_claim_pickup",
            {
                "p_claim_id": cid,
                "p_actor_id": str(user["id"]),
                "p_candidate_hash": hash_code(code, cid, secret),
            },
        ).execute()
    except Exception as exc:                 # noqa: BLE001
        logger.error("confirm_claim_pickup failed: %s", type(exc).__name__)
        raise HandshakeError(503, "pickup_service_unavailable")

    outcome = result.data
    if outcome == "ok":
        return {"status": "completed", "claim_id": cid}
    if outcome in RESULT_ERRORS:
        status_code, detail = RESULT_ERRORS[outcome]
        raise HandshakeError(status_code, detail)
    logger.error("confirm_claim_pickup returned an unexpected result")
    raise HandshakeError(503, "pickup_service_unavailable")


def donor_handshake_code(client: Any, claim_id: Any, user: Dict[str, Any]) -> Dict[str, Any]:
    """The code for the donor who owns the listing, while the claim is active."""
    secret = get_secret()
    if secret is None:
        raise HandshakeError(503, "handshake_not_configured")
    cid = normalize_claim_id(claim_id)
    if cid is None:
        raise HandshakeError(404, "not_found")
    try:
        claims = (
            client.table("claims")
            .select("id, listing_id, status, handshake_expires_at")
            .eq("id", cid)
            .limit(1)
            .execute()
            .data
            or []
        )
        claim = claims[0] if claims else None
        listing = None
        if claim:
            listings = (
                client.table("food_listings")
                .select("donor_id")
                .eq("id", claim["listing_id"])
                .limit(1)
                .execute()
                .data
                or []
            )
            listing = listings[0] if listings else None
    except Exception as exc:                 # noqa: BLE001
        logger.error("donor handshake lookup failed: %s", type(exc).__name__)
        raise HandshakeError(503, "pickup_service_unavailable")

    # Anyone who is not the owning donor gets the same answer as a missing claim.
    if not claim or not listing or str(listing.get("donor_id")) != str(user["id"]):
        raise HandshakeError(404, "not_found")
    if claim.get("status") != "active":
        raise HandshakeError(409, "claim_not_active")
    if not claim.get("handshake_expires_at"):
        raise HandshakeError(409, "no_handshake")
    return {"code": derive_code(cid, secret), "expires_at": claim["handshake_expires_at"]}
