
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from app.core.auth import get_current_donor, get_current_verified_receiver
from app.core.config import settings
from app.core.supabase_client import get_supabase
from app.handshake.routes import VerifyCodeRequest, get_pickup_code, verify_pickup_code
from app.handshake.service import derive_code, hash_code

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claims", tags=["Claims"])


class ClaimRequest(BaseModel):
    listing_id: UUID


@router.post("/", status_code=status.HTTP_200_OK)
@router.post("/create", status_code=status.HTTP_200_OK)
def create_claim(
    request: ClaimRequest,
    user=Depends(get_current_verified_receiver),
):
    client = get_supabase()

    try:
        # Generate the claim ID before calling Supabase.
        claim_id = str(uuid4())

        # Generate the donor's pickup code.
        pickup_code = derive_code(
            claim_id,
            settings.HANDSHAKE_SECRET,
        )

        # Store only the keyed hash in the database.
        handshake_code_hash = hash_code(
            pickup_code,
            claim_id,
            settings.HANDSHAKE_SECRET,
        )

        response = client.rpc(
            "claim_food_listing",
            {
                "p_listing_id": str(request.listing_id),
                "p_receiver_id": user["id"],
                "p_claim_id": claim_id,
                "p_handshake_code_hash": handshake_code_hash,
            },
        ).execute()

        data = response.data

        if not data or not data.get("success"):
            error_msg = (
                data.get("message", "Listing unavailable")
                if data else "Claim rejected"
            )

            code = (
                str(data.get("code", "")).upper()
                if isinstance(data, dict) else ""
            )

            if (
                code == "CONFLICT"
                or "already claimed" in error_msg.lower()
                or "active claim" in error_msg.lower()
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This listing has already been claimed by another receiver.",
                )

            if (
                code == "EXPIRED"
                or "expired" in error_msg.lower()
                or "safe_until" in error_msg.lower()
            ):
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="This food listing has expired and can no longer be claimed.",
                )

            if code == "FORBIDDEN":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Verified receiver access required",
                )

            if code == "NOT_FOUND":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Listing not found",
                )

            if code == "INVALID_HANDSHAKE":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Pickup handshake could not be created",
                )

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Listing cannot be claimed in its current state",
            )

        # Never expose the pickup code or its hash to the receiver.
        return {
            "message": "Food listing claimed successfully",
            "claim": data,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Supabase claim_food_listing failed: %s",
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Claim service temporarily unavailable",
        )


@router.get("/my")
def get_my_claims(
    user=Depends(get_current_verified_receiver),
):
    try:
        client = get_supabase()

        response = (
            client.table("claims")
            .select("id, listing_id, status, claimed_at, expires_at")
            .eq("receiver_id", user["id"])
            .order("claimed_at", desc=True)
            .execute()
        )

        results = []

        for claim in response.data or []:
            listing_response = (
                client.table("food_listings")
                .select(
                    "id, title, description, food_category, quantity, "
                    "servings, safe_until, status, created_at, "
                    "pickup_address, latitude, longitude"
                )
                .eq("id", claim["listing_id"])
                .limit(1)
                .execute()
            )

            listing = (
                listing_response.data[0]
                if listing_response.data else None
            )

            if listing:
                expiry = datetime.fromisoformat(
                    claim["expires_at"].replace("Z", "+00:00")
                )

                is_active = (
                    claim["status"] == "active"
                    and expiry > datetime.now(timezone.utc)
                )

                listing_safe = (
                    datetime.fromisoformat(
                        listing["safe_until"].replace("Z", "+00:00")
                    ) > datetime.now(timezone.utc)
                )

                if not (is_active and listing_safe):
                    listing.pop("pickup_address", None)
                    listing.pop("latitude", None)
                    listing.pop("longitude", None)

                results.append({
                    "claim": claim,
                    "listing": listing,
                })

        return {
            "count": len(results),
            "claims": results,
        }

    except Exception as exc:
        logger.exception(
            "Could not retrieve receiver claims: %s",
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Claim service temporarily unavailable",
        )


@router.post("/{claim_id}/cancel")
def cancel_claim(
    claim_id: UUID,
    user=Depends(get_current_verified_receiver),
):
    try:
        client = get_supabase()

        response = client.rpc(
            "cancel_food_claim",
            {
                "p_claim_id": str(claim_id),
                "p_receiver_id": user["id"],
            },
        ).execute()

        result = response.data

        if not result or not result.get("success"):
            code = (
                result.get("code")
                if isinstance(result, dict) else None
            )

            http_code = (
                status.HTTP_404_NOT_FOUND if code == "NOT_FOUND"
                else status.HTTP_403_FORBIDDEN if code == "FORBIDDEN"
                else status.HTTP_409_CONFLICT
            )

            raise HTTPException(
                status_code=http_code,
                detail="Claim cannot be cancelled in its current state",
            )

        if result.get("claim_status") == "expired":
            return {
                "message": "This claim had already expired.",
                "result": result,
            }

        return {
            "message": "Claim cancelled successfully.",
            "result": result,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Supabase cancel_food_claim failed: %s",
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Claim service temporarily unavailable",
        )


@router.post("/{claim_id}/verify", status_code=status.HTTP_200_OK)
@router.post("/{claim_id}/verify-pickup", status_code=status.HTTP_200_OK)
def verify_claim_pickup_alias(
    claim_id: UUID,
    request: VerifyCodeRequest,
    user=Depends(get_current_verified_receiver),
):
    """Compatibility alias for POST /handshake/claims/{claim_id}/verify."""
    return verify_pickup_code(claim_id=claim_id, request=request, receiver=user)


@router.get("/{claim_id}/code", status_code=status.HTTP_200_OK)
def get_claim_code_alias(
    claim_id: UUID,
    response: Response,
    donor=Depends(get_current_donor),
):
    """Compatibility alias for GET /handshake/claims/{claim_id}/code."""
    return get_pickup_code(claim_id=claim_id, response=response, donor=donor)
