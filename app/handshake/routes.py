
"""Pickup handshake API routes."""

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.core.auth import get_current_donor, get_current_verified_receiver
from app.core.config import settings
from app.core.supabase_client import get_supabase
from app.handshake.service import derive_code, hash_code

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/handshake", tags=["Pickup Handshake"])


class VerifyCodeRequest(BaseModel):
    code: str = Field(pattern=r"^[0-9]{4}$")


def _parse_datetime(value):
    """Parse an ISO datetime returned by Supabase."""
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _one_row(response):
    """Return the first Supabase row, or None."""
    rows = response.data or []
    return rows[0] if rows else None


def _rpc_result(data):
    """Normalize a JSONB RPC result."""
    if isinstance(data, list):
        return data[0] if data else {}
    return data if isinstance(data, dict) else {}


@router.get("/claims/{claim_id}/code")
def get_pickup_code(
    claim_id: UUID,
    response: Response,
    donor=Depends(get_current_donor),
):
    """Return the pickup code only to the donor who owns the listing."""

    # Prevent browsers and intermediaries from caching pickup codes.
    response.headers["Cache-Control"] = "no-store"

    client = get_supabase()

    try:
        claim = _one_row(
            client.table("claims")
            .select("id, listing_id, status, expires_at")
            .eq("id", str(claim_id))
            .limit(1)
            .execute()
        )

        # Do not disclose whether a claim exists to an unrelated donor.
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")

        listing = _one_row(
            client.table("food_listings")
            .select("id, donor_id, status, safe_until")
            .eq("id", claim["listing_id"])
            .limit(1)
            .execute()
        )

        if not listing or str(listing["donor_id"]) != str(donor["id"]):
            raise HTTPException(status_code=404, detail="Claim not found")

        if claim["status"] != "active" or listing["status"] != "claimed":
            raise HTTPException(
                status_code=409,
                detail="This claim is no longer active",
            )

        now = datetime.now(timezone.utc)
        claim_expiry = _parse_datetime(claim.get("expires_at"))
        food_expiry = _parse_datetime(listing.get("safe_until"))

        if not claim_expiry or now >= claim_expiry:
            raise HTTPException(status_code=410, detail="Claim has expired")

        if not food_expiry or now >= food_expiry:
            raise HTTPException(status_code=410, detail="Food is no longer safe")

        handshake = _one_row(
            client.table("pickup_handshakes")
            .select("claim_id, verified_at, invalidated_at")
            .eq("claim_id", str(claim_id))
            .limit(1)
            .execute()
        )

        if not handshake:
            raise HTTPException(
                status_code=409,
                detail="Pickup handshake is unavailable",
            )

        if handshake.get("invalidated_at"):
            raise HTTPException(
                status_code=409,
                detail="Pickup handshake has been invalidated",
            )

        if handshake.get("verified_at"):
            raise HTTPException(
                status_code=409,
                detail="Pickup has already been verified",
            )

        code = derive_code(str(claim_id), settings.HANDSHAKE_SECRET)

        return {
            "claim_id": str(claim_id),
            "pickup_code": code,
            "expires_at": claim["expires_at"],
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("Could not retrieve pickup code")
        raise HTTPException(
            status_code=503,
            detail="Pickup code service temporarily unavailable",
        )


@router.post("/claims/{claim_id}/verify")
def verify_pickup_code(
    claim_id: UUID,
    request: VerifyCodeRequest,
    receiver=Depends(get_current_verified_receiver),
):
    """Verify the receiver's code through an atomic database RPC."""
    try:
        candidate_hash = hash_code(
            request.code,
            str(claim_id),
            settings.HANDSHAKE_SECRET,
        )

        response = get_supabase().rpc(
            "verify_pickup_handshake",
            {
                "p_claim_id": str(claim_id),
                "p_receiver_id": str(receiver["id"]),
                "p_candidate_hash": candidate_hash,
            },
        ).execute()

        result = _rpc_result(response.data)
        outcome = result.get("code")

        if result.get("success") is True or outcome == "OK":
            return {
                "message": "Pickup verified successfully",
                "claim_id": str(claim_id),
                "claim_status": "completed",
                "listing_status": "picked_up",
                "verified_at": result.get("verified_at"),
            }

        errors = {
            "WRONG_CODE": (400, "Incorrect pickup code"),
            "LOCKED": (423, "Pickup verification is locked after five incorrect attempts"),
            "EXPIRED": (410, "Claim or food has expired"),
            "ALREADY_USED": (409, "Pickup has already been verified"),
            "INVALIDATED": (409, "Pickup handshake has been invalidated"),
            "NO_HANDSHAKE": (409, "Pickup handshake is unavailable"),
            "NOT_FOUND": (404, "Claim not found"),
            "FORBIDDEN": (403, "This claim does not belong to this receiver"),
            "CONFLICT": (409, "Claim is no longer available for pickup"),
        }

        status_code, message = errors.get(
            outcome,
            (500, "Pickup verification could not be completed"),
        )
        raise HTTPException(status_code=status_code, detail=message)

    except HTTPException:
        raise
    except Exception:
        logger.exception("Pickup verification failed")
        raise HTTPException(
            status_code=503,
            detail="Pickup verification service temporarily unavailable",
        )
