import logging
from app.core.supabase_client import get_supabase
from app.jobs.timeout_strikes import apply_timeout_strikes

logger = logging.getLogger("sharemeal.jobs")


def run_expiry_and_timeout_sweep() -> dict:
    """Run the single transactional PostgreSQL sweep (FR-08, FR-09, BR-04),
    then persist timeout strikes for claims that genuinely timed out.

    The return value is the sweep result, unchanged. Strike processing is idempotent and derives
    eligibility from stored claim state, so a failure here is safe to retry and never loses strikes.
    """
    try:
        db = get_supabase()
        response = db.rpc("process_expired_claims_and_listings", {}).execute()
    except Exception:
        logger.exception("Transactional expiry sweep failed")
        raise
    result = response.data
    if not isinstance(result, dict):
        raise RuntimeError("Expiry sweep returned an unexpected response")
    logger.info("Expiry sweep completed: %s", result)

    strikes = apply_timeout_strikes(db)
    logger.info("Timeout strikes applied: %s", strikes)
    return result
