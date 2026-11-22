"""Matching demo on seeded data (Member 2). Run from the project folder:

    python scripts/demo_matching.py

Shows the alert tiers widening over time for ONE new listing. No database,
no network. Distances and timings are unvalidated placeholders, not
food-safety rules.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.listings.geo import distance_km  # noqa: E402
from app.matching.scheduler import plan_alerts  # noqa: E402

START = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)
LISTING = {
    "id": "demo-listing", "latitude": 12.9716, "longitude": 77.5946,
    "food_category": "human", "status": "available",
    "created_at": START, "safe_until": START + timedelta(hours=4),
}


def make(name, km, **overrides):
    receiver = {
        "id": name,
        "latitude": LISTING["latitude"] + km / 111.0,   # roughly km north of the listing
        "longitude": LISTING["longitude"],
        "approval_status": "approved", "is_verified": True,
        "is_flagged": False, "accepts_food_category": "human",
    }
    receiver.update(overrides)
    return receiver


ELIGIBLE = [
    make("Asha Trust", 0.8), make("Seva Foundation", 1.2), make("Hope Shelter", 1.6),
    make("Annapurna NGO", 2.0), make("Karuna Home", 2.4), make("Roti Bank", 2.8),
    make("Sneha Kendra", 5.0), make("Jeevan Trust", 7.0), make("Far Away NGO", 12.0),
]
NEVER = {
    "Paws Animal Home": ("animal home, this listing is for people", dict(accepts_food_category="animal")),
    "Unapproved NGO": ("not approved by an admin yet", dict(approval_status="pending", is_verified=False)),
    "Flagged NGO": ("flagged after 3 no-shows", dict(is_flagged=True)),
}
RECEIVERS = ELIGIBLE + [make(name, 0.6, **extra) for name, (_, extra) in NEVER.items()]


def main():
    print("New listing: cooked food for people (human). Receivers seeded: %d\n" % len(RECEIVERS))
    notified = []
    for minutes in (0, 5, 10):
        now = START + timedelta(minutes=minutes)
        new = plan_alerts(LISTING, RECEIVERS, notified, now)
        print("Minute %2d: %d new alert(s)" % (minutes, len(new)))
        for receiver in new:
            km = distance_km(LISTING["latitude"], LISTING["longitude"],
                             receiver["latitude"], receiver["longitude"])
            print("    %-18s %5.1f km" % (receiver["id"], km))
        notified.extend(r["id"] for r in new)
    print("\nNever alerted:")
    for name, (why, _) in NEVER.items():
        print("    %-18s %s" % (name, why))
    assert not set(NEVER) & set(notified), "an excluded receiver was alerted"
    print("\nTiers (placeholders): nearest 5 within 3 km, 8 km after 5 min, everyone after 10 min.")


if __name__ == "__main__":
    main()
