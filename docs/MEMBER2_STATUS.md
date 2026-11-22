# Member 2 status: matching, alerts and verification

Offline test suite: 193 passed, 4 skipped.

## Built and tested offline
- Tiered matching: nearest 5 within 3 km, 8 km after 5 min, everyone after 10 min.
  Only approved, verified, unflagged receivers whose food category fits.
- Receiver location API: PUT/GET /receivers/me/location (receiver_locations table).
- Pickup handshake: 4-digit code, only a keyed hash stored, 5 wrong attempts lock,
  expiry, replay protection. Routes: POST /claims/{id}/confirm-pickup and
  GET /donor/claims/{id}/handshake-code.
- No-show strikes: idempotent, flag at 3, admin clear, food-expiry is not a strike.
- Alert planning and delivery logic (push first, Telegram fallback, failures never
  change claim state).

## Built, works live only after the SQL in docs/ is applied
- Handshake and strikes need docs/proposed_member2_migration.sql (part 1).
- Admin audit and flag clearing need part 2.
- Receiver locations need the receiver_locations migration.
- The SQL has been reviewed by hand and with Member 1 but has NOT been run on a
  real database by Member 2.

## Not built
- Alert job running every minute (needs part 3 SQL, on hold).
- Web push (service worker, VAPID keys, subscribe endpoint).
- Telegram bot.
- /admin screen, strike counts and handshake review queue in the UI.

## Demo without a database
    python scripts/demo_matching.py

## Known limitations
- Distances, tiers and the safe window are placeholders, not validated food-safety
  rules. Check FSSAI guidance before the pitch.
- HANDSHAKE_SECRET must be set on the server (16+ random characters). If it is
  missing, the handshake is skipped with a warning.
- Demos use mock OTP. On iPhones web push needs the app added to the home screen.

## Update: alerts (branch feature/member-2-alerts)
Offline test suite: 203 passed, 4 skipped.
- Alert job: runs after each expiry sweep, applies the matching tiers, records who was
  alerted (alert_deliveries) and failed attempts (alert_attempts). Never raises.
- In-app alert: GET /receivers/me/alerts lists listings the receiver was alerted about.
- Telegram sender: built and tested offline. Off unless TELEGRAM_BOT_TOKEN is set, and
  receivers cannot link a chat yet (no bot /start flow).
- Part 3 SQL (docs/proposed_member2_migration_part3.sql): for review, NOT applied.
- Seed script: scripts/seed_receiver_locations.py (dry run by default).
- Still not built: web push, Telegram /start linking, /admin screen.
