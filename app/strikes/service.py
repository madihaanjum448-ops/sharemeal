"""No-show strike logic (Member 2). Pure functions, no database.

Strikes are an append-only list of events. The count is derived from the
events, never stored as a bare counter, so every strike is auditable.
FLAG_THRESHOLD is a placeholder pending team sign-off (PRD OD-09).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple

FLAG_THRESHOLD = 3
EVENT_TIMEOUT = "timeout"
EVENT_ADMIN_CLEAR = "admin_clear"


@dataclass(frozen=True)
class StrikeEvent:
    receiver_id: str
    claim_id: str
    event_type: str
    reason: str
    created_at: datetime


def _since_last_clear(events: List[StrikeEvent], receiver_id: str) -> List[StrikeEvent]:
    mine = [e for e in events if e.receiver_id == receiver_id]
    last_clear = -1
    for index, event in enumerate(mine):
        if event.event_type == EVENT_ADMIN_CLEAR:
            last_clear = index
    return mine[last_clear + 1:]


def strike_count(events: List[StrikeEvent], receiver_id: str) -> int:
    return sum(
        1 for e in _since_last_clear(events, receiver_id)
        if e.event_type == EVENT_TIMEOUT
    )


def is_flagged(
    events: List[StrikeEvent], receiver_id: str, threshold: int = FLAG_THRESHOLD
) -> bool:
    return strike_count(events, receiver_id) >= threshold


def record_timeout_strike(
    events: List[StrikeEvent],
    receiver_id: str,
    claim_id: str,
    now: datetime,
    reason: str = "claim timed out",
) -> Tuple[List[StrikeEvent], bool]:
    """Return (new event list, strike_added). Safe to call repeatedly.

    A claim can produce at most one timeout strike, however many times the
    timeout job retries. The input list is never modified.
    """
    already = any(
        e.claim_id == claim_id and e.event_type == EVENT_TIMEOUT for e in events
    )
    if already:
        return list(events), False
    event = StrikeEvent(receiver_id, claim_id, EVENT_TIMEOUT, reason, now)
    return list(events) + [event], True


def admin_clear_flag(
    events: List[StrikeEvent],
    receiver_id: str,
    admin_id: str,
    now: datetime,
    reason: str = "admin review",
) -> List[StrikeEvent]:
    """Record an admin review. Strikes counted from this point restart at 0.

    Old events stay in the list, so the history is never erased.
    """
    claim_marker = "admin:%s" % admin_id
    event = StrikeEvent(receiver_id, claim_marker, EVENT_ADMIN_CLEAR, reason, now)
    return list(events) + [event]
