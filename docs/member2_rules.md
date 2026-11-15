# Member 2 Rules: Matching, Alerts and Verification
Status: DRAFT for team review. All distances and timings are unvalidated placeholders.

## Handshake
- 4-digit code per claim, generated at claim start; only a hash is stored
- Shown to the donor; receiver types it at pickup
- 5 wrong attempts lock the claim; code is invalid after expiry, cancel or completion
- Completion happens exactly once

## Strikes
- A timed-out claim adds 1 strike (one per claim, idempotent)
- At 3 strikes the receiver is flagged and excluded from matching until admin review

## Matching tiers
- 0-5 min: nearest 5 within 3 km
- 5-10 min: widen to 8 km
- 10+ min: all compatible receivers
- Only approved, unflagged receivers whose accepted category fits the listing

## Needed from Member 1
- user_profiles: accepts_food_category, is_flagged
- claims (or a new table): handshake hash, expiry, attempts
- a receiver_strike_events table, unique per (claim_id, event_type)
