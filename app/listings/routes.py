from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import get_current_donor, get_current_user
from app.core.supabase_client import get_supabase
from app.listings.schemas import FoodListingCreate, FoodListingDetailResponse, FoodListingPublicResponse

router = APIRouter(prefix="/listings", tags=["Food Listings"])

PUBLIC_FIELDS = (
    "id, title, description, food_category, quantity, "
    "servings, safe_until, status, created_at"
)

PRIVATE_FIELDS = (
    "id, donor_id, title, description, food_category, quantity, "
    "servings, safe_until, status, created_at, pickup_address, latitude, longitude"
)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_listing(
    listing: FoodListingCreate,
    donor=Depends(get_current_donor),
):
    client = get_supabase()

    listing_data = listing.model_dump(mode="json")
    listing_data["donor_id"] = donor["id"]
    listing_data["status"] = "available"

    try:
        response = client.table("food_listings").insert(listing_data).execute()

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create food listing",
            )

        return {
            "message": "Food listing created successfully",
            "listing": response.data[0],
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the listing",
        )


@router.get("/")
def get_available_listings(
    category: Optional[str] = Query(default=None, pattern="^(human|animal)$"),
    limit: int = Query(default=20, ge=1, le=100),
):
    client = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    try:
        query = (
            client.table("food_listings")
            .select(PUBLIC_FIELDS)
            .eq("status", "available")
            .gt("safe_until", now)
            .order("created_at", desc=True)
            .limit(limit)
        )

        if category:
            query = query.eq("food_category", category)

        response = query.execute()

        return {
            "count": len(response.data or []),
            "listings": response.data or [],
        }

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not retrieve food listings",
        )


@router.get("/{listing_id}")
def get_listing_details(
    listing_id: UUID,
    current_user=Depends(get_current_user),
):
    client = get_supabase()

    try:
        response = (
            client.table("food_listings")
            .select(PRIVATE_FIELDS)
            .eq("id", str(listing_id))
            .limit(1)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Food listing not found",
            )

        listing = response.data[0]

        # Privacy Enforcement (BR-06): Reveal exact pickup address and GPS pin
        # ONLY if the user is the donor owner OR holds an active/completed claim on this listing.
        is_owner = listing.get("donor_id") == current_user["id"]
        is_authorized_receiver = False

        if current_user["role"] == "receiver" and current_user.get("is_verified"):
            claim_check = (
                client.table("claims")
                .select("id, status")
                .eq("listing_id", str(listing_id))
                .eq("receiver_id", current_user["id"])
                .in_("status", ["active", "completed", "picked_up"])
                .execute()
            )
            if claim_check.data:
                is_authorized_receiver = True

        if not (is_owner or is_authorized_receiver):
            listing.pop("pickup_address", None)
            listing.pop("latitude", None)
            listing.pop("longitude", None)

        listing.pop("donor_id", None)
        return {"listing": listing}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not retrieve listing details",
        )