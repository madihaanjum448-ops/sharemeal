"""Run the no-show strike function (Member 2). Never raises."""
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def run_timeout_strikes(client: Any) -> Optional[int]:
    """Call apply_timeout_strikes(). A failure here must never stop the expiry sweep."""
    try:
        result = client.rpc("apply_timeout_strikes", {}).execute()
    except Exception as exc:                 # noqa: BLE001
        logger.error("timeout strike run failed: %s", type(exc).__name__)
        return None
    data = result.data
    if isinstance(data, bool) or not isinstance(data, int):
        return None
    if data:
        logger.info("timeout strikes recorded: %s", data)
    return data
