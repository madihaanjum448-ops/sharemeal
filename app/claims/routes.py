from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import get_current_verified_receiver
from app.core.supabase_client import get_supabase

router = APIRouter(prefix="/claims", tags=["Claims"])


class ClaimRequest(BaseModel):
    listing_id: UUID


@router.post("/", status_code=status.HTTP_200_OK)
def create_claim(
    request: ClaimRequest,
    user=Depends(get_current_verified_receiver),
):
    client = get_supabase()

    try:
        response = client.rpc(
            "claim_food_listing",
            {
                "p_listing_id": str(request.listing_id),
                "p_receiver_id": user["id"],
            },
        ).execute()

        data = response.data

        if not data or not data.get("success"):
            error_msg = data.get("message", "Listing unavailable") if data else "Claim rejected"
            
            if "already claimed" in error_msg.lower() or "active claim" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This listing has already been claimed by another receiver.",
                )
            if "expired" in error_msg.lower() or "safe_until" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="This food listing has expired and can no longer be claimed.",
                )
            
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg,
            )

        return {
            "message": "Food listing claimed successfully",
            "claim": data,
        }

    except HTTPException:
        raise
    except Exception as error:
        err_str = str(error).lower()
        if "409" in err_str or "unique constraint" in err_str or "lock" in err_str:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Simultaneous claim detected. Another organisation successfully claimed this food first.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not process claim request",
        )


@router.get("/my")
def get_my_claims(user=Depends(get_current_verified_receiver)):
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
                    "servings, safe_until, status, created_at, pickup_address, latitude, longitude"
                )
                .eq("id", claim["listing_id"])
                .limit(1)
                .execute()
            )

            listing = listing_response.data[0] if listing_response.data else None

            if listing:
                expiry = datetime.fromisoformat(
                    claim["expires_at"].replace("Z", "+00:00")
                )

                is_active_or_completed = (
                    claim["status"] in ["active", "completed", "picked_up"]
                    and (claim["status"] != "active" or expiry > datetime.now(timezone.utc))
                )

                if not is_active_or_completed:
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

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve your claims",
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

        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not cancel claim.",
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
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not cancel this claim. It may already be completed or expired.",
        )