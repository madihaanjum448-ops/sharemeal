from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from fastapi import HTTPException

_lock = Lock()
_events = defaultdict(deque)


def enforce_otp_send_limit(key: str, max_events: int, window_seconds: int) -> None:
    now = monotonic()
    with _lock:
        events = _events[key]
        while events and now - events[0] >= window_seconds:
            events.popleft()
        if len(events) >= max_events:
            raise HTTPException(status_code=429, detail="Too many OTP requests. Please try again later.")
        events.append(now)
        if len(_events) > 10000:
            stale = [k for k, q in _events.items() if not q or now - q[-1] >= window_seconds]
            for k in stale:
                _events.pop(k, None)
