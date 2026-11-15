# Member 1 repair implementation notes

## Implemented in this repair copy

- Fail-fast settings validation and documented required environment variables.
- Verified receiver and admin dependencies; profile database failures return 503 rather than being mislabeled as bad tokens.
- OTP send/verify throttling for a single process, redacted logging, configurable 6/8 digit OTP length, and signup-only profile fields.
- Structured HTTP/validation/unhandled error envelopes with request IDs.
- Periodic expiry sweep task in the FastAPI lifespan; manual sweep endpoint now requires admin.
- Removed the non-transactional Python fallback. The worker calls one PostgreSQL transaction/RPC and fails visibly if it is unavailable.
- Added repeatable migration files for core table baseline, indexes, atomic claim/cancel/expiry/edit functions, and RLS/service-role grants.
- Claim RPC reconciles stale timed-out claims before deciding whether a new claim can proceed; database unique partial index remains the final invariant.
- Food expiry takes precedence over claim timeout and closes an active claim in the same transaction.
- Address/coordinates removed from public feed; exact pickup information is returned only to donor owner or verified receiver with an active unexpired claim while food remains safe.
- Added donor's own listings, atomic edit/cancel RPC endpoints, and bounded Haversine radius filtering.
- Added API contract, migration inspection SQL, invariant inspection SQL, and basic unit tests for geospatial/rate-limit helpers.

## Not verified in this environment

- No live Supabase connection was made and no SQL migration was applied. Run the read-only inspection SQL first, back up the project, then review and apply migrations in order.
- PostgreSQL syntax/behaviour was not executed against a PostgreSQL server here.
- `pytest` could not be run in this environment because FastAPI/Pydantic/pytest/Supabase packages are not installed and package downloads are unavailable. Python compileall succeeded; the standalone Haversine smoke checks succeeded.
- No real OTP, claim concurrency, RLS, scheduler deployment, or API integration test was run.

## Important deployment limitations / team decisions

- The expiry scheduler runs inside the API process. Use one dedicated worker or a distributed lock if deploying multiple API replicas.
- OTP throttling is in-memory and single-process only; use Redis or gateway-level limits for multi-instance deployment.
- Radius filtering currently examines at most 500 candidate rows using Haversine. Use PostGIS/geospatial indexes before production scale and agree radius semantics with Members 2 and 4.
- Donor cancellation while a claim is active is rejected until PRD OD-03 is approved.
- Exact address visibility after completed pickup remains a team decision (OD-01); this repair uses the stricter active-claim-only policy.
- The migrations assume the current known columns in `user_profiles`, `food_listings` and `claims`. Compare the live schema with `00_inspect_live_schema.sql` before applying.
