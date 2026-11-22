import logging

from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.auth import get_current_verified_receiver
from app.core.supabase_client import get_supabase
from app.notifications.service import listing_deep_link

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/receivers", tags=["Alerts"])


@router.get("/me/alerts")
def my_alerts(response: Response, user=Depends(get_current_verified_receiver)):
    """Listings this receiver was alerted about that are still available."""
    response.headers["Cache-Control"] = "no-store"
    client = get_supabase()
    try:
        rows = (
            client.table("alert_deliveries").select("listing_id, created_at")
            .eq("receiver_id", str(user["id"])).execute().data or []
        )
        ids = [r["listing_id"] for r in rows]
        live = set()
        if ids:
            listings = client.table("food_listings").select("id, status").in_("id", ids).execute().data or []
            live = {item["id"] for item in listings if item.get("status") == "available"}
    except Exception as exc:                       # noqa: BLE001
        logger.error("alerts lookup failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="alerts_unavailable")
    newest_first = sorted(rows, key=lambda r: str(r.get("created_at")), reverse=True)
    return {
        "alerts": [
            {"listing_id": r["listing_id"], "alerted_at": r.get("created_at"),
             "url": listing_deep_link(r["listing_id"])}
            for r in newest_first if r["listing_id"] in live
        ][:50]
    }
