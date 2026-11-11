from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import get_current_donor
from app.core.supabase_client import get_supabase
from app.listings.schemas import FoodListingCreate

router = APIRouter(prefix="/listings", tags=["Food Listings"])


PUBLIC_FIELDS = (
    "id, title, description, food_category, quantity, "
    "servings, safe_until, status, created_at"
)


@router.post("/", status_code=201)
def create_listing(
    listing: FoodListingCreate,
    donor=Depends(get_current_donor),
):
    client = get_supabase()

    listing_data = listing.model_dump(mode="json")
    listing_data["donor_id"] = donor["id"]

    try:
        response = (
            client.table("food_listings")
            .insert(listing_data)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=500,
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
            status_code=500,
            detail="An error occurred while creating the listing",
        )


@router.get("/")
def get_available_listings(
    category: str | None = Query(default=None, pattern="^(human|animal)$"),
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
            "count": len(response.data),
            "listings": response.data,
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve food listings",
        )


@router.get("/{listing_id}")
def get_listing_details(listing_id: UUID):
    client = get_supabase()

    try:
        response = (
            client.table("food_listings")
            .select(PUBLIC_FIELDS)
            .eq("id", str(listing_id))
            .limit(1)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Food listing not found",
            )

        return {"listing": response.data[0]}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve listing details",
        )