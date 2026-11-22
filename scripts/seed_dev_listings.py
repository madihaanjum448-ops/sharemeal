import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx

ITEMS = [
    ("[DEV-SEED] Fresh vegetable meal boxes", "human", "10 meal boxes", 10),
    ("[DEV-SEED] Cooked rice and dal", "human", "5 kg", 20),
    ("[DEV-SEED] Fresh fruit packets", "human", "15 packets", 15),
    ("[DEV-SEED] Bread and bakery surplus", "human", "20 packets", 20),
    ("[DEV-SEED] Vegetable pulao", "human", "8 containers", 8),
    ("[DEV-SEED] Chapati and curry packs", "human", "12 packs", 12),
    ("[DEV-SEED] Fresh bananas", "human", "3 dozen", 36),
    ("[DEV-SEED] Packed lunch meals", "human", "10 meals", 10),
    ("[DEV-SEED] Fresh tomatoes and onions", "human", "8 kg", 0),
    ("[DEV-SEED] Rice and sambar meals", "human", "15 portions", 15),
    ("[DEV-SEED] Sealed dry pet food", "animal", "5 kg", 0),
    ("[DEV-SEED] Packaged dog food", "animal", "10 packets", 0),
    ("[DEV-SEED] Cat food packets", "animal", "12 packets", 0),
    ("[DEV-SEED] Fresh pet-safe vegetables", "animal", "3 kg", 0),
    ("[DEV-SEED] Sealed animal feed", "animal", "4 kg", 0),
]

def main():
    parser = argparse.ArgumentParser(description="Create development-only ShareMeal listings.")
    parser.add_argument("--confirm", action="store_true", help="Confirm creation of demo listings.")
    parser.add_argument("--allow-remote", action="store_true", help="Allow a non-local API URL.")
    args = parser.parse_args()

    if not args.confirm:
        sys.exit("Nothing created. Re-run with --confirm after checking the target environment.")

    base_url = os.getenv("SHAREMEAL_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    token = os.getenv("SHAREMEAL_SEED_ACCESS_TOKEN", "").strip()

    parsed = urlparse(base_url)
    local_hosts = {"localhost", "127.0.0.1"}
    if parsed.scheme != "https" and parsed.hostname not in local_hosts:
        sys.exit("Refusing non-local HTTP URL. Use HTTPS for remote environments.")
    if parsed.hostname not in local_hosts and not args.allow_remote:
        sys.exit("Refusing remote API. Pass --allow-remote only for a dedicated test environment.")
    if not token:
        sys.exit("Set SHAREMEAL_SEED_ACCESS_TOKEN to a donor access token. Do not paste it into chat.")

    headers = {"Authorization": f"Bearer {token}"}
    safe_until = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    with httpx.Client(base_url=base_url, headers=headers, timeout=20) as client:
        existing_response = client.get("/listings/my")
        existing_response.raise_for_status()
        existing_data = existing_response.json()
        existing = existing_data.get("listings", []) if isinstance(existing_data, dict) else []
        existing_titles = {item.get("title") for item in existing}

        created = 0
        skipped = 0
        for title, category, quantity, servings in ITEMS:
            if title in existing_titles:
                skipped += 1
                print(f"SKIP already exists: {title}")
                continue

            payload = {
                "title": title,
                "description": "DEVELOPMENT DEMO DATA ONLY. Not a real food donation.",
                "food_category": category,
                "quantity": quantity,
                "servings": servings if servings > 0 else None,
                "pickup_address": "DEMO ONLY - NOT A REAL PICKUP LOCATION",
                "latitude": 12.9716,
                "longitude": 77.5946,
                "safe_until": safe_until,
            }
            response = client.post("/listings/", json=payload)
            if response.is_error:
                print(f"FAILED ({response.status_code}): {title} - {response.text[:300]}")
                response.raise_for_status()
            created += 1
            print(f"CREATED: {title}")

    print(f"\nFinished. Created: {created}; skipped existing: {skipped}.")
    print("These are demo records. Cancel or remove them before any real-world use.")

if __name__ == "__main__":
    main()
