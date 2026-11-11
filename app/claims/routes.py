
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.supabase_client import get_supabase

router = APIRouter(prefix="/claims", tags=["Claims"])


class ClaimRequest(BaseModel):
    listing_id: UUID


def require_receiver(user):
    if user["role"] != "receiver":
        raise HTTPException(
            status_code=403,
            detail="Only receivers can access this feature",
        )

    if not user["is_verified"]:
        raise HTTPException(
            status_code=403,
            detail="Your receiver account must be verified",
        )


@router.post("/")
def create_claim(
    request: ClaimRequest,
    user=Depends(get_current_user),
):
    require_receiver(user)

    try:
        client = get_supabase()

        response = client.rpc(
            "claim_food_listing",
            {
                "p_listing_id": str(request.listing_id),
                "p_receiver_id": user["id"],
            },
        ).execute()

        return {
            "message": "Food listing claimed successfully",
            "claim": response.data,
        }

    except Exception as error:
        print("CLAIM ERROR:", repr(error))
        raise HTTPException(
            status_code=400,
            detail="Could not claim this listing. It may already be claimed, expired, or unavailable.",
        )


@router.get("/my")
def get_my_claims(user=Depends(get_current_user)):
    require_receiver(user)

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
                    "servings, safe_until, status, created_at, pickup_address"
                )
                .eq("id", claim["listing_id"])
                .limit(1)
                .execute()
            )

            listing = (
                listing_response.data[0]
                if listing_response.data
                else None
            )

            if listing:
                expiry = datetime.fromisoformat(
                    claim["expires_at"].replace("Z", "+00:00")
                )

                is_active = (
                    claim["status"] == "active"
                    and expiry > datetime.now(timezone.utc)
                )

                listing_details = {
                    key: value
                    for key, value in listing.items()
                    if key != "pickup_address"
                }

                if is_active:
                    listing_details["pickup_address"] = (
                        listing["pickup_address"]
                    )

                results.append({
                    "claim": claim,
                    "listing": listing_details,
                })

        return {
            "count": len(results),
            "claims": results,
        }

    except Exception as error:
        print("GET MY CLAIMS ERROR:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve your claims",
        )


@router.post("/{claim_id}/cancel")
def cancel_claim(
    claim_id: UUID,
    user=Depends(get_current_user),
):
    require_receiver(user)

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

        if result.get("claim_status") == "expired":
            return {
                "message": "This claim had already expired.",
                "result": result,
            }

        return {
            "message": "Claim cancelled successfully.",
            "result": result,
        }

    except Exception as error:
        print("CANCEL CLAIM ERROR:", repr(error))
        raise HTTPException(
            status_code=400,
            detail="Could not cancel this claim. It may already be completed, cancelled, or expired.",
        )
