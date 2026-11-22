"""Give approved receivers test locations in Bengaluru (Member 2).

    python scripts/seed_receiver_locations.py            # dry run, changes nothing
    python scripts/seed_receiver_locations.py --apply    # writes to receiver_locations

Locations are PLACEHOLDERS for testing, not real NGO addresses. It only touches
receivers that are approved and have no location yet. Needs the migrations applied.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SPOTS = [
    ("MG Road", 12.9757, 77.6068), ("Indiranagar", 12.9784, 77.6408),
    ("Koramangala", 12.9352, 77.6245), ("Jayanagar", 12.9308, 77.5838),
    ("Malleshwaram", 13.0035, 77.5710), ("Whitefield", 12.9698, 77.7500),
    ("Hebbal", 13.0358, 77.5970), ("Electronic City", 12.8452, 77.6602),
]


def main():
    from app.core.supabase_client import get_supabase

    apply = "--apply" in sys.argv
    client = get_supabase()
    receivers = (client.table("user_profiles").select("id")
                 .eq("role", "receiver").eq("approval_status", "approved").execute().data or [])
    have = {r["receiver_id"] for r in (client.table("receiver_locations").select("receiver_id").execute().data or [])}
    todo = [r["id"] for r in receivers if r["id"] not in have]
    print("approved receivers without a location: %d" % len(todo))
    for index, rid in enumerate(todo):
        name, lat, lng = SPOTS[index % len(SPOTS)]
        print("  %s -> %s (%.4f, %.4f)" % (rid, name, lat, lng))
        if apply:
            client.table("receiver_locations").upsert(
                {"receiver_id": rid, "latitude": lat, "longitude": lng}, on_conflict="receiver_id").execute()
    print("written" if apply else "dry run only: add --apply to write")


if __name__ == "__main__":
    main()
