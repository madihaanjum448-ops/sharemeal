import logging
from datetime import datetime, timezone
from app.core.supabase_client import get_supabase

logger = logging.getLogger("sharemeal.jobs")


def run_expiry_and_timeout_sweep() -> dict:
    """
    Executes background cleanup for expired 15-minute claims and safe-until food listings (FR-08, FR-09, BR-04)[cite: 1].
    """
    client = get_supabase()
    now_iso = datetime.now(timezone.utc).isoformat()
    
    summary = {
        "expired_claims": 0,
        "reopened_listings": 0,
        "expired_listings": 0,
    }

    try:
        rpc_sweep = client.rpc("process_expired_claims_and_listings", {}).execute()
        if rpc_sweep.data:
            logger.info(f"Database sweep job executed successfully: {rpc_sweep.data}")
            return rpc_sweep.data
    except Exception as e:
        logger.warning(f"RPC process_expired_claims_and_listings fallback triggered: {e}")

    try:
        # 1. Sweep expired active claims
        expired_claims_res = (
            client.table("claims")
            .select("id, listing_id")
            .eq("status", "active")
            .lte("expires_at", now_iso)
            .execute()
        )

        for claim in expired_claims_res.data or []:
            claim_id = claim["id"]
            listing_id = claim["listing_id"]

            client.table("claims").update({"status": "expired"}).eq("id", claim_id).execute()
            summary["expired_claims"] += 1

            listing_res = client.table("food_listings").select("safe_until").eq("id", listing_id).single().execute()
            if listing_res.data:
                safe_until_dt = datetime.fromisoformat(listing_res.data["safe_until"].replace("Z", "+00:00"))
                if safe_until_dt > datetime.now(timezone.utc):
                    client.table("food_listings").update({"status": "available"}).eq("id", listing_id).execute()
                    summary["reopened_listings"] += 1
                else:
                    client.table("food_listings").update({"status": "expired"}).eq("id", listing_id).execute()
                    summary["expired_listings"] += 1

        # 2. Sweep available listings past safe_until
        expired_food_res = (
            client.table("food_listings")
            .update({"status": "expired"})
            .eq("status", "available")
            .lte("safe_until", now_iso)
            .execute()
        )
        if expired_food_res.data:
            summary["expired_listings"] += len(expired_food_res.data)

    except Exception as err:
        logger.error(f"Error during fallback expiry sweep: {err}")

    return summary