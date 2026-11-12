
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import get_current_donor, get_current_user
from app.core.supabase_client import get_supabase
from app.listings.schemas import FoodListingCreate, FoodListingUpdate
from app.listings.geo import distance_km

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
        response = (
            client.table("food_listings")
            .insert(listing_data)
            .execute()
        )

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
    category: Optional[str] = Query(
        default=None,
        pattern="^(human|animal)$",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10000),
    latitude: Optional[float] = Query(default=None, ge=-90, le=90),
    longitude: Optional[float] = Query(default=None, ge=-180, le=180),
    radius_km: Optional[float] = Query(default=None, gt=0, le=100),
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
            .range(offset, offset + limit - 1)
        )

        if category:
            query = query.eq("food_category", category)

        response = query.execute()
        listings = response.data or []

        if any(v is not None for v in (latitude, longitude, radius_km)):
            if (
                latitude is None
                or longitude is None
                or radius_km is None
            ):
                raise HTTPException(
                    status_code=422,
                    detail="latitude, longitude and radius_km must be supplied together",
                )

            # Bound the database result before applying Haversine distance filtering.
            candidates = (
                client.table("food_listings")
                .select(
                    "id, title, description, food_category, quantity, "
                    "servings, safe_until, status, created_at, latitude, longitude"
                )
                .eq("status", "available")
                .gt("safe_until", now)
                .limit(500)
                .execute()
                .data or []
            )

            candidates = [
                item for item in candidates
                if not category or item["food_category"] == category
            ]

            candidates.sort(
                key=lambda item: distance_km(
                    latitude,
                    longitude,
                    item["latitude"],
                    item["longitude"],
                )
            )

            listings = [
                item for item in candidates
                if distance_km(
                    latitude,
                    longitude,
                    item["latitude"],
                    item["longitude"],
                ) <= radius_km
            ]

            listings = listings[offset:offset + limit]

            for item in listings:
                item.pop("latitude", None)
                item.pop("longitude", None)

        return {
            "count": len(listings),
            "listings": listings,
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not retrieve food listings",
        )


@router.get("/my")
def get_my_listings(
    donor=Depends(get_current_donor),
    limit: int = Query(default=50, ge=1, le=100),
):
    try:
        response = (
            get_supabase()
            .table("food_listings")
            .select(PRIVATE_FIELDS)
            .eq("donor_id", donor["id"])
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return {
            "count": len(response.data or []),
            "listings": response.data or [],
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve your listings",
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

        # Privacy Enforcement (BR-06):
        # Reveal exact pickup address and GPS pin only to:
        # 1. The donor who owns the listing.
        # 2. An approved, verified receiver with an active,
        #    unexpired claim while the food is still safe.

        is_owner = listing.get("donor_id") == current_user["id"]
        is_authorized_receiver = False

        if (
            current_user["role"] == "receiver"
            and current_user.get("is_verified") is True
            and current_user.get("approval_status") == "approved"
        ):
            claim_check = (
                client.table("claims")
                .select("id, status, expires_at")
                .eq("listing_id", str(listing_id))
                .eq("receiver_id", current_user["id"])
                .eq("status", "active")
                .execute()
            )

            now = datetime.now(timezone.utc)

            is_authorized_receiver = any(
                claim.get("status") == "active"
                and datetime.fromisoformat(
                    claim["expires_at"].replace("Z", "+00:00")
                ) > now
                and datetime.fromisoformat(
                    listing["safe_until"].replace("Z", "+00:00")
                ) > now
                for claim in (claim_check.data or [])
            )

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


@router.patch("/{listing_id}")
def update_listing(
    listing_id: UUID,
    changes: FoodListingUpdate,
    donor=Depends(get_current_donor),
):
    payload = changes.model_dump(
        exclude_unset=True,
        mode="json",
    )

    if not payload:
        raise HTTPException(
            status_code=422,
            detail="At least one field must be supplied",
        )

    try:
        result = (
            get_supabase()
            .rpc(
                "update_food_listing",
                {
                    "p_listing_id": str(listing_id),
                    "p_donor_id": donor["id"],
                    "p_changes": payload,
                },
            )
            .execute()
            .data
        )

        if not result or not result.get("success"):
            code = result.get("code") if isinstance(result, dict) else None

            raise HTTPException(
                status_code=404 if code == "NOT_FOUND" else 409,
                detail="Listing cannot be edited in its current state",
            )

        return {
            "message": "Listing updated",
            "result": result,
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not update listing",
        )


@router.post("/{listing_id}/cancel")
def cancel_listing(
    listing_id: UUID,
    donor=Depends(get_current_donor),
):
    try:
        result = (
            get_supabase()
            .rpc(
                "cancel_donor_listing",
                {
                    "p_listing_id": str(listing_id),
                    "p_donor_id": donor["id"],
                },
            )
            .execute()
            .data
        )

        if not result or not result.get("success"):
            code = result.get("code") if isinstance(result, dict) else None

            raise HTTPException(
                status_code=404 if code == "NOT_FOUND" else 409,
                detail="Listing cannot be cancelled in its current state",
            )

        return {
            "message": "Listing cancelled",
            "result": result,
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not cancel listing",
        )
