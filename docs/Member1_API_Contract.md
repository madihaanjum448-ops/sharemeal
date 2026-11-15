# ShareMeal Member 1 API Contract (prototype)

Base URL: `http://localhost:8000`. Protected routes require `Authorization: Bearer <Supabase access_token>`.
All timestamps are ISO-8601 with timezone offsets; server/database time is authoritative.

## Authentication

### `POST /auth/send-otp`
Request: `{"email":"person@example.com"}`
Success: `{"message":"Verification code sent. Please check your email."}`
Errors: `422 VALIDATION_ERROR`, `429` rate limited, `503` provider unavailable.

### `POST /auth/verify-otp`
Request for a new profile: `{"email":"person@example.com","token":"12345678","full_name":"A Person","role":"donor"}`. Existing users may omit profile creation fields.
Success returns `user`, `profile` and `session.access_token` / `session.refresh_token`.

## Listings

### `POST /listings/` (donor)
Request:
```json
{"title":"Vegetable pulao","description":"Prepared this morning","food_category":"human","quantity":"5 containers","servings":10,"pickup_address":"Example pickup address","latitude":12.9716,"longitude":77.5946,"safe_until":"2026-11-12T18:00:00+05:30"}
```
Success: `201` with `listing`. Only donors may create listings.

### `GET /listings/?category=human&limit=20&offset=0`
Returns available, unexpired listings. Public fields exclude exact address and coordinates.
Optional nearby query: `latitude`, `longitude`, and `radius_km` must all be supplied together. Current prototype filters at most 500 candidate rows using Haversine distance; confirm scale/radius policy before production.

### `GET /listings/{listing_id}`
Requires authentication. Exact pickup address/coordinates are returned only to the donor owner or a verified receiver with a non-expired active claim while the listing is still safe. Other authenticated users receive public fields only.

### `GET /listings/my` (donor)
Returns the donor's own listings including pickup details.

### `PATCH /listings/{listing_id}` (donor owner)
Request contains one or more editable listing fields. Only available listings with no active claim may be edited. Uses the atomic `update_food_listing` RPC.

### `POST /listings/{listing_id}/cancel` (donor owner)
Cancels only an available listing without an active claim. Active-claim donor cancellation remains disabled pending PRD decision OD-03.

## Claims

### `POST /claims/` (verified receiver)
Request: `{"listing_id":"<uuid>"}`. Uses the atomic `claim_food_listing` RPC. Success returns a claim with a 15-minute expiry. Conflict returns `409`; expired food returns `410`; unverified receiver returns `403`.

### `GET /claims/my` (verified receiver)
Returns the receiver's claims. Exact pickup details appear only for an active, unexpired claim while the listing remains within `safe_until`.

### `POST /claims/{claim_id}/cancel` (verified receiver / claim owner)
Uses atomic `cancel_food_claim`. The listing reopens only when still safe; otherwise it becomes expired.

## Operations

### `GET /health`
Checks database connectivity.

### `POST /jobs/trigger-sweep` (admin only)
Manually runs the transactional expiry sweep. The app also runs the sweep on the configured interval in a single-process deployment.

## Error envelope

```json
{"error":{"code":"HTTP_409","message":"Listing cannot be claimed in its current state","request_id":"<uuid>"}}
```
Validation errors use `VALIDATION_ERROR` and include field details. Never expose database exception text, secrets or tokens.
