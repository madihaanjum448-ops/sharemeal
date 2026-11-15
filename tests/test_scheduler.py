from datetime import datetime, timedelta, timezone

from app.matching.scheduler import minutes_since, plan_alerts

START = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)


def listing(**overrides):
    base = {
        "latitude": 12.9716, "longitude": 77.5946, "food_category": "human",
        "status": "available", "created_at": START,
        "safe_until": START + timedelta(hours=4),
    }
    base.update(overrides)
    return base


def make(rid, offset_deg):
    return {
        "id": rid, "latitude": 12.9716 + offset_deg, "longitude": 77.5946,
        "approval_status": "approved", "is_verified": True,
        "is_flagged": False, "accepts_food_category": "human",
    }


def ids(result):
    return [r["id"] for r in result]


NEAR = make("near", 0.01)   # about 1.1 km
MID = make("mid", 0.05)     # about 5.5 km
FAR = make("far", 0.10)     # about 11 km


def test_minutes_since_is_never_negative():
    assert minutes_since(START, START - timedelta(minutes=3)) == 0.0


def test_first_run_alerts_only_the_near_tier():
    assert ids(plan_alerts(listing(), [NEAR, MID, FAR], [], START)) == ["near"]


def test_rerun_sends_no_duplicates():
    assert plan_alerts(listing(), [NEAR, MID, FAR], ["near"], START) == []


def test_tier_widening_adds_only_new_receivers():
    at5 = START + timedelta(minutes=5)
    assert ids(plan_alerts(listing(), [NEAR, MID, FAR], ["near"], at5)) == ["mid"]


def test_after_ten_minutes_everyone_remaining_is_alerted():
    at10 = START + timedelta(minutes=10)
    result = plan_alerts(listing(), [NEAR, MID, FAR], ["near", "mid"], at10)
    assert ids(result) == ["far"]


def test_claimed_listing_sends_nothing():
    assert plan_alerts(listing(status="claimed"), [NEAR], [], START) == []


def test_expired_listing_sends_nothing():
    late = START + timedelta(hours=4)
    assert plan_alerts(listing(), [NEAR], [], late) == []


def test_flagged_receiver_never_alerted():
    flagged = dict(NEAR, is_flagged=True)
    assert plan_alerts(listing(), [flagged], [], START) == []
