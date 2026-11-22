
import logging

logger = logging.getLogger("sharemeal.jobs")


class TimeoutStrikeError(RuntimeError):
    """Timeout-strike processing failed after the expiry sweep completed."""


def apply_timeout_strikes(db) -> dict:
    """Persist timeout strikes for genuine receiver claim timeouts.

    Calls the transactional apply_timeout_strikes() PostgreSQL function.
    The database function is idempotent: a claim can produce at most one
    strike, regardless of how many times this function runs.

    Reuses the caller's database client.
    """
    try:
        response = db.rpc("apply_timeout_strikes", {}).execute()
    except Exception as exc:
        logger.exception("Timeout strike processing failed")
        raise TimeoutStrikeError(
            "Timeout strike processing failed after the expiry sweep completed"
        ) from exc

    result = response.data

    if (
        not isinstance(result, dict)
        or type(result.get("strikes_added")) is not int
    ):
        raise TimeoutStrikeError(
            "Timeout strike processing returned an unexpected response"
        )

    return result
