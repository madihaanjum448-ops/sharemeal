# ShareMeal API Contract

**Version:** 1.0 (Draft)  
**Project:** ShareMeal  
**Backend:** FastAPI + Supabase  
**Base URL (local):** `http://127.0.0.1:8000`

## 1. Purpose

This document defines the API endpoints, request formats, response formats, authentication requirements and error handling rules for ShareMeal.

It acts as the common integration reference for the backend, donor frontend, receiver frontend and admin workflows.

**Important:** Examples containing UUIDs, access tokens and timestamps are illustrative. Actual values are returned by the backend.

## 2. Authentication

Protected endpoints require the following header:

```http
Authorization: Bearer <access_token>
```

### 2.1 Send OTP

- **Method:** POST
- **Endpoint:** `/auth/send-otp`
- **Access:** Public

**Request:**

```json
{
  "email": "receiver@example.com"
}
```

**Success — 200 OK:**

```json
{
  "message": "Verification code sent. Please check your email."
}
```

**Possible errors:**
- `422` — Invalid email.
- `429` — OTP send rate limit exceeded.
- `503` — OTP delivery unavailable.

### 2.2 Verify OTP / Register / Login

- **Method:** POST
- **Endpoint:** `/auth/verify-otp`
- **Access:** Public

**Request:**

```json
{
  "email": "shelter@example.com",
  "token": "123456",
  "full_name": "Hope Animal Shelter",
  "role": "receiver",
  "organization_name": "Hope Animal Shelter"
}
```

**Field rules:**

| Field | Required in schema | Validation |
|---|---|---|
| email | Yes | Valid email |
| token | Yes | 6–8 numeric digits |
| full_name | No | 2–100 characters |
| role | No | `donor` or `receiver` |
| organization_name | No | Maximum 160 characters |

For a new profile, `full_name` and `role` are required by the backend route.

**Illustrative success — 200 OK:**

```json
{
  "message": "Email verified and login successful.",
  "user": {
    "id": "user-uuid",
    "email": "shelter@example.com"
  },
  "profile": {
    "id": "user-uuid",
    "full_name": "Hope Animal Shelter",
    "role": "receiver",
    "organization_name": "Hope Animal Shelter",
    "is_verified": false,
    "approval_status": "pending"
  },
  "session": {
    "access_token": "<access-token>",
    "refresh_token": "<refresh-token>",
    "token_type": "bearer",
    "expires_in": 3600
  }
}
```

**Possible errors:**
- `401` — OTP verification failed.
- `422` — Missing required new-profile information.
- `429` — Verification rate limit exceeded.
- `500` — Account setup failed.

### 2.3 Receiver approval states

| Status | Meaning |
|---|---|
| `pending` | Awaiting administrator review |
| `approved` | Approved to use receiver-only claim functionality |
| `rejected` | Receiver application rejected |

New receiver profiles are created with `approval_status = pending` and `is_verified = false`.

Approved receivers require both `approval_status = approved` and `is_verified = true`.

Donor profiles have `approval_status = null`.

## 3. Food Listings APIs

### 3.1 Create Food Listing

- **Method:** POST
- **Endpoint:** `/listings/`
- **Access:** Authenticated donor

**Request headers:**

```http
Authorization: Bearer <donor_access_token>
Content-Type: application/json
```

**Request body:**

```json
{
  "title": "Fresh Vegetable Rice",
  "description": "Freshly prepared vegetable rice",
  "food_category": "human",
  "quantity": "5 kg",
  "servings": 20,
  "pickup_address": "123 Main Road, Bengaluru",
  "latitude": 13.1007,
  "longitude": 77.5963,
  "safe_until": "2026-11-13T18:00:00+05:30"
}
```

**Field rules:**

| Field | Required | Validation |
|---|---|---|
| title | Yes | 3–120 characters |
| description | No | Optional text |
| food_category | Yes | `human` or `animal` |
| quantity | Yes | 1–100 characters |
| servings | No | Positive integer |
| pickup_address | Yes | Minimum 5 characters |
| latitude | Yes | -90 to 90 |
| longitude | Yes | -180 to 180 |
| safe_until | Yes | Future timestamp with timezone |

The backend assigns `donor_id` from the authenticated user and sets listing `status` to `available`.

**Success — 201 Created:**

```json
{
  "message": "Food listing created successfully",
  "listing": {
    "id": "listing-uuid",
    "donor_id": "donor-uuid",
    "title": "Fresh Vegetable Rice",
    "description": "Freshly prepared vegetable rice",
    "food_category": "human",
    "quantity": "5 kg",
    "servings": 20,
    "pickup_address": "123 Main Road, Bengaluru",
    "latitude": 13.1007,
    "longitude": 77.5963,
    "safe_until": "2026-11-13T18:00:00+05:30",
    "status": "available",
    "created_at": "2026-11-12T10:00:00+00:00"
  }
}
```

**Possible errors:**
- `401` — Missing or invalid authentication.
- `403` — User is not a donor.
- `422` — Invalid request.
- `500` — Listing creation failed.

### 3.2 Browse Available Listings

- **Method:** GET
- **Endpoint:** `/listings/`
- **Access:** Public

**Query parameters:**

| Parameter | Default | Validation |
|---|---|---|
| category | None | `human` or `animal` |
| limit | 20 | 1–100 |
| offset | 0 | 0–10000 |
| latitude | None | -90 to 90 |
| longitude | None | -180 to 180 |
| radius_km | None | Greater than 0, maximum 100 |

**Example:**

```http
GET /listings/?category=human&limit=20&offset=0
```

**Location-filtered example:**

```http
GET /listings/?category=human&latitude=13.1007&longitude=77.5963&radius_km=10
```

When location filtering is used, latitude, longitude and radius must all be supplied.

**Success — 200 OK:**

```json
{
  "count": 1,
  "listings": [
    {
      "id": "listing-uuid",
      "title": "Fresh Vegetable Rice",
      "description": "Freshly prepared vegetable rice",
      "food_category": "human",
      "quantity": "5 kg",
      "servings": 20,
      "safe_until": "2026-11-13T18:00:00+05:30",
      "status": "available",
      "created_at": "2026-11-12T10:00:00+00:00"
    }
  ]
}
```

Exact pickup addresses and GPS coordinates are excluded from browse results.

**Possible errors:**
- `422` — Invalid query parameters or incomplete location filter.
- `503` — Could not retrieve listings.

### 3.3 View My Listings

- **Method:** GET
- **Endpoint:** `/listings/my`
- **Access:** Authenticated donor

**Example:**

```http
GET /listings/my?limit=50
```

**Success — 200 OK:**

```json
{
  "count": 1,
  "listings": [
    {
      "id": "listing-uuid",
      "donor_id": "donor-uuid",
      "title": "Fresh Vegetable Rice",
      "food_category": "human",
      "quantity": "5 kg",
      "servings": 20,
      "safe_until": "2026-11-13T18:00:00+05:30",
      "status": "available",
      "created_at": "2026-11-12T10:00:00+00:00",
      "pickup_address": "123 Main Road, Bengaluru",
      "latitude": 13.1007,
      "longitude": 77.5963
    }
  ]
}
```

### 3.4 View Listing Details

- **Method:** GET
- **Endpoint:** `/listings/{listing_id}`
- **Access:** Authenticated user

**Example:**

```http
GET /listings/550e8400-e29b-41d4-a716-446655440000
```

**Success — 200 OK:**

```json
{
  "listing": {
    "id": "listing-uuid",
    "title": "Fresh Vegetable Rice",
    "food_category": "human",
    "quantity": "5 kg",
    "servings": 20,
    "safe_until": "2026-11-13T18:00:00+05:30",
    "status": "available",
    "created_at": "2026-11-12T10:00:00+00:00"
  }
}
```

Exact pickup details are disclosed only to the donor who owns the listing or a receiver who has a currently active, unexpired claim while the food remains within its safety deadline.

**Possible errors:**
- `401` — Authentication required.
- `404` — Listing not found.
- `503` — Could not retrieve listing details.

### 3.5 Edit Listing

- **Method:** PATCH
- **Endpoint:** `/listings/{listing_id}`
- **Access:** Authenticated donor; database RPC checks ownership and listing state.

**Request body:**

```json
{
  "quantity": "7 kg",
  "servings": 25,
  "description": "Updated food quantity"
}
```

Only supplied fields are included in the update.

**Success — 200 OK (illustrative):**

```json
{
  "message": "Listing updated",
  "result": {
    "success": true
  }
}
```

**Possible errors:**
- `401` — Authentication required.
- `403` — User is not a donor.
- `404` — Listing not found.
- `409` — Listing cannot be edited in its current state.
- `422` — Empty or invalid update.
- `503` — Update service unavailable.

### 3.6 Cancel Listing

- **Method:** POST
- **Endpoint:** `/listings/{listing_id}/cancel`
- **Access:** Authenticated donor; database RPC checks ownership and listing state.

No request body is required.

**Success — 200 OK (illustrative):**

```json
{
  "message": "Listing cancelled",
  "result": {
    "success": true
  }
}
```

**Possible errors:**
- `401` — Authentication required.
- `403` — User is not a donor.
- `404` — Listing not found.
- `409` — Listing cannot be cancelled in its current state.
- `503` — Cancellation service unavailable.

## 4. Privacy and Integration Rules

1. Donor identity and exact pickup location must not be exposed in public listing browse results.
2. Exact pickup details are disclosed only under the authorised conditions described in the listing details endpoint.
3. Donor-only endpoints must use donor authentication.
4. Receiver claim functionality requires an approved and verified receiver.
5. The frontend must use the access token returned by OTP verification for protected API calls.
6. The frontend must not decide or assign donor IDs, receiver IDs, listing status or approval status.

## 5. Contract Status

This document currently covers Authentication and Food Listings.

Claims, Admin, Pickup/Handshake, Notifications and Impact endpoints will be added after their route implementations and team integration requirements are verified.

**Document status:** Draft — pending team review and endpoint testing.
## 6. Claims APIs

Claims allow approved receiver organisations to reserve available food listings.

A successful claim creates a **15-minute claim window**. The listing becomes unavailable to other receivers while the claim is active.

All claims endpoints require an authenticated, approved and verified receiver.

### 6.1 Create a Food Claim

- **Method:** POST
- **Endpoint:** `/claims/`
- **Access:** Approved receiver only

**Request headers:**

```http
Authorization: Bearer <receiver_access_token>
Content-Type: application/json
```

**Request body:**

```json
{
  "listing_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

The listing ID must refer to an existing available food listing.

**Success — 200 OK:**

```json
{
  "message": "Food listing claimed successfully",
  "claim": {
    "success": true,
    "claim_id": "claim-uuid",
    "listing_id": "listing-uuid",
    "status": "active",
    "expires_at": "2026-11-12T10:15:00+00:00"
  }
}
```

**Business rules:**

1. Only approved and verified receivers can claim food.
2. The listing must have `status = available`.
3. The food must not have passed its `safe_until` deadline.
4. The database locks the listing during the claim operation to prevent simultaneous claims.
5. A successful claim remains active for 15 minutes.
6. The listing status changes to `claimed`.
7. A listing cannot have multiple active claims.

**Possible errors:**

| Status | Meaning |
|---|---|
| 401 | Missing or invalid authentication |
| 403 | Receiver is not approved or verified |
| 404 | Listing not found |
| 409 | Listing already claimed or unavailable |
| 410 | Food listing has expired |
| 422 | Invalid listing ID or request body |
| 503 | Claim service unavailable |

### 6.2 View My Claims

- **Method:** GET
- **Endpoint:** `/claims/my`
- **Access:** Approved receiver only

**Request:**

```http
GET /claims/my
Authorization: Bearer <receiver_access_token>
```

No request body is required.

**Success — 200 OK:**

```json
{
  "count": 1,
  "claims": [
    {
      "claim": {
        "id": "claim-uuid",
        "listing_id": "listing-uuid",
        "status": "active",
        "claimed_at": "2026-11-12T10:00:00+00:00",
        "expires_at": "2026-11-12T10:15:00+00:00"
      },
      "listing": {
        "id": "listing-uuid",
        "title": "Fresh Vegetable Rice",
        "description": "Freshly prepared vegetable rice",
        "food_category": "human",
        "quantity": "5 kg",
        "servings": 20,
        "safe_until": "2026-11-12T18:00:00+05:30",
        "status": "claimed",
        "created_at": "2026-11-12T09:00:00+00:00",
        "pickup_address": "123 Main Road, Bengaluru",
        "latitude": 13.1007,
        "longitude": 77.5963
      }
    }
  ]
}
```

The example represents an active, unexpired claim with food that remains within its safety deadline.

**Privacy rule:**

Exact pickup details are included only when the claim is active, its 15-minute expiry has not passed, and the food is still within its safety deadline.

Otherwise, `pickup_address`, `latitude` and `longitude` are omitted from the listing object.

**Possible errors:**

| Status | Meaning |
|---|---|
| 401 | Missing or invalid authentication |
| 403 | Receiver is not approved or verified |
| 503 | Could not retrieve claims |

### 6.3 Cancel a Food Claim

- **Method:** POST
- **Endpoint:** `/claims/{claim_id}/cancel`
- **Access:** Approved receiver who owns the claim

**Request:**

```http
POST /claims/550e8400-e29b-41d4-a716-446655440000/cancel
Authorization: Bearer <receiver_access_token>
```

No request body is required.

**Success — 200 OK:**

```json
{
  "message": "Claim cancelled successfully.",
  "result": {
    "success": true,
    "claim_status": "cancelled"
  }
}
```

The result fields are illustrative; the actual response depends on the database RPC.

If the claim has already expired, the route can return:

```json
{
  "message": "This claim had already expired.",
  "result": {
    "success": true,
    "claim_status": "expired"
  }
}
```

**Possible errors:**

| Status | Meaning |
|---|---|
| 401 | Missing or invalid authentication |
| 403 | Receiver is not approved, verified or authorised |
| 404 | Claim not found |
| 409 | Claim cannot be cancelled in its current state |
| 422 | Invalid claim ID |
| 503 | Claim cancellation service unavailable |

### 6.4 Claim Status Reference

| Status | Meaning |
|---|---|
| `active` | Claim is currently active |
| `completed` | Claim has been completed |
| `cancelled` | Claim was cancelled |
| `expired` | Claim window expired |

### 6.5 Claims Integration Notes

For the receiver frontend:

1. Display the claim countdown using the returned `expires_at` timestamp.
2. Refresh claim information from `GET /claims/my` rather than relying only on the frontend countdown.
3. Display exact pickup information only when it is returned by the backend.
4. Handle `409` and `410` responses by informing the receiver that the listing is no longer claimable.
5. Do not allow pending or rejected receiver accounts to access claim functionality.

The backend remains responsible for enforcing claim expiry, listing availability, receiver approval and pickup-location privacy.

## 7. Admin APIs — Receiver Verification

**Access:** Admin only  
**Authentication:** Required — Supabase access token  
**Base path:** `/admin`

These APIs allow administrators to review receiver applications and approve or reject organisations requesting access to ShareMeal.

### 7.1 Get Pending Receiver Applications

**Endpoint:** `GET /admin/receivers/pending`

**Purpose:** Retrieve all receiver accounts awaiting administrator approval.

**Request:** No request body.

**Success response — 200 OK:**

```json
{
  "count": 2,
  "receivers": [
    {
      "id": "receiver-uuid",
      "full_name": "Example User",
      "phone": "9876543210",
      "organization_name": "Example NGO",
      "approval_status": "pending",
      "is_verified": false,
      "created_at": "2026-11-12T10:00:00Z"
    }
  ]
}
```

### 7.2 Get Receiver Application Details

**Endpoint:** `GET /admin/receivers/{receiver_id}`

**Purpose:** View an individual receiver's application.

**Path parameter:**

| Parameter | Type | Description |
|---|---|---|
| receiver_id | UUID | Receiver's profile ID |

**Success response — 200 OK:**

```json
{
  "receiver": {
    "id": "receiver-uuid",
    "full_name": "Example User",
    "phone": "9876543210",
    "role": "receiver",
    "organization_name": "Example NGO",
    "approval_status": "pending",
    "is_verified": false,
    "created_at": "2026-11-12T10:00:00Z"
  }
}
```

### 7.3 Approve Receiver Application

**Endpoint:** `PATCH /admin/receivers/{receiver_id}/approve`

**Purpose:** Approve a pending receiver account.

**Request:** No request body.

**Backend actions:**
- Changes `approval_status` to `approved`.
- Changes `is_verified` to `true`.
- Allows the receiver to access features requiring verified receiver permissions.

**Success response — 200 OK:**

```json
{
  "message": "Receiver approved successfully",
  "receiver": {
    "id": "receiver-uuid",
    "approval_status": "approved",
    "is_verified": true
  }
}
```

### 7.4 Reject Receiver Application

**Endpoint:** `PATCH /admin/receivers/{receiver_id}/reject`

**Purpose:** Reject a pending receiver account.

**Request:** No request body.

**Backend actions:**
- Changes `approval_status` to `rejected`.
- Changes `is_verified` to `false`.

**Success response — 200 OK:**

```json
{
  "message": "Receiver rejected successfully",
  "receiver": {
    "id": "receiver-uuid",
    "approval_status": "rejected",
    "is_verified": false
  }
}
```

### 7.5 Admin API Error Responses

| HTTP status | Meaning | When it occurs |
|---|---|---|
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | Authenticated user is not an administrator |
| 404 | Not Found | Receiver application does not exist |
| 409 | Conflict | Application is no longer pending or its status changed |
| 422 | Validation Error | Invalid UUID or request validation failure |
| 503 | Service Unavailable | Database operation failed |

**Error response format:**

```json
{
  "error": {
    "code": "HTTP_404",
    "message": "Receiver application not found",
    "request_id": "request-uuid"
  }
}
```

### 7.6 Security and Business Rules

1. All four endpoints require administrator authentication.
2. Only accounts with the `receiver` role can be reviewed.
3. Only applications with `approval_status = pending` can be approved or rejected.
4. Approval sets `is_verified = true`.
5. Rejection sets `is_verified = false`.
6. Repeated approval or rejection attempts are rejected with HTTP 409.
7. Receiver application information, including phone numbers and organisation details, is restricted to administrators.

**Implementation status:** Implemented in `app/admin/routes.py` and registered in `app/main.py`.

**Integration note:** The admin frontend should use these endpoints to display pending applications, view application details, and submit approval or rejection actions.

*Note: Response examples are illustrative. The actual receiver object returned by the update endpoints may contain additional profile fields.*