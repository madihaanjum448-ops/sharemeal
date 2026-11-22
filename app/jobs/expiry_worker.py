import logging
from app.core.supabase_client import get_supabase
from app.strikes.rpc import run_timeout_strikes  # MEMBER2-HOOK

logger = logging.getLogger("sharemeal.jobs")


def run_expiry_and_timeout_sweep() -> dict:
    """Run the single transactional PostgreSQL sweep (FR-08, FR-09, BR-04)."""
    try:
        response = get_supabase().rpc("process_expired_claims_and_listings", {}).execute()
    except Exception:
        logger.exception("Transactional expiry sweep failed")
        raise
    result = response.data
    if not isinstance(result, dict):
        raise RuntimeError("Expiry sweep returned an unexpected response")
    logger.info("Expiry sweep completed: %s", result)
    # MEMBER2-HOOK: record no-show strikes. A failure here never stops the sweep.
    run_timeout_strikes(get_supabase())
    return result
