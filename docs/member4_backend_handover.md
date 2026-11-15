# Member 1 → Member 4 Backend Integration Handover
**ShareMeal Backend Services for Receiver Frontend**

- **Author:** Member 1 (Backend Engineer)
- **Target Audience:** Member 4 (Receiver Frontend Engineer)
- **Frontend Stack:** React 19, Vite 8, React Router 7 (`http://localhost:5173`)
- **Backend Stack:** FastAPI, Supabase Python Client (`http://localhost:8000`)
- **Integration Status:** Backend changes verified offline (63 passed, 0 failed, 4 skipped in offline testing; no live Supabase integration claimed)
---

## 1. Quickstart & Server Execution

### 1.1 Starting the FastAPI Backend
Ensure your Python virtual environment is activated and dependencies are installed:
```powershell
# In sharemeal-fixed:
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```
- **Base URL:** `http://localhost:8000`
- **Interactive Swagger Docs:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **Health Check:** `GET http://localhost:8000/health`

### 1.2 CORS Configuration
The backend is pre-configured with FastAPI's `CORSMiddleware` supporting browser requests from your development server:
- **Allowed Origins:** `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`, `http://127.0.0.1:3000`
- **Allow Credentials:** `true` (supports cookies and authorization headers)
- **Allowed Methods:** `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`, `PATCH`
- **Allowed Headers:** `Content-Type`, `Authorization`, `X-Request-ID`, `Accept`
- **Exposed Headers:** `X-Request-ID`, `Date`

---

## 2. Authentication & Session Integration

All authenticated requests require the standard Bearer header:
```http
Authorization: Bearer <access_token>
```

### 2.1 Send OTP (`POST /auth/send-otp`)
Initiates passwordless magic link / OTP authentication via email.
- **Endpoint:** `POST /auth/send-otp`
- **Auth Required:** No
- **Request Body:**
```json
{
  "email": "receiver@example.com"
}
```
- **Response (200 OK):**
```json
{
  "message": "Verification code sent. Please check your email."
}
```

### 2.2 Verify OTP (`POST /auth/verify-otp`)
Verifies the token sent to the user's email and establishes a Supabase session.
- **Endpoint:** `POST /auth/verify-otp`
- **Auth Required:** No
- **Request Body:**
```json
{
  "email": "receiver@example.com",
  "token": "123456"
}
```
- **Response (200 OK):**
```json
{
  "message": "Email verified and login successful.",
  "user": {
    "id": "a0000000-0000-0000-0000-000000000001",
    "email": "receiver@example.com"
  },
  "profile": {
    "id": "a0000000-0000-0000-0000-000000000001",
    "full_name": "Priya Sharma",
    "role": "receiver",
    "organization_name": null,
    "is_verified": true,
    "approval_status": "approved"
  },
  "session": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "v1.mr...",
    "token_type": "bearer",
    "expires_in": 3600
  } 
} 
```

### 2.3 Get Current User Profile (`GET /auth/me`)
Retrieves the logged-in user's profile metadata from the Supabase `user_profiles` table. The response provides profile attributes at the top level, as well as mirrored inside nested `user` and `profile` objects for frontend compatibility.

- **Endpoint:** `GET /auth/me`
- **Auth Required:** Yes (`Bearer <access_token>`)
- **Headers:** `Authorization: Bearer <access_token>`
- **Response (200 OK):**
```json
{
  "id": "a0000000-0000-0000-0000-000000000001",
  "email": "receiver@example.com",
  "full_name": "Priya Sharma",
  "role": "receiver",
  "organization_name": null,
  "is_verified": true,
  "approval_status": "approved",
  "created_at": "2026-11-14T10:00:00Z",
  "user": {
    "id": "a0000000-0000-0000-0000-000000000001",
    "email": "receiver@example.com",
    "full_name": "Priya Sharma",
    "role": "receiver",
    "organization_name": null,
    "is_verified": true,
    "approval_status": "approved",
    "created_at": "2026-11-14T10:00:00Z"
  },
  "profile": {
    "id": "a0000000-0000-0000-0000-000000000001",
    "email": "receiver@example.com",
    "full_name": "Priya Sharma",
    "role": "receiver",
    "organization_name": null,
    "is_verified": true,
    "approval_status": "approved",
    "created_at": "2026-11-14T10:00:00Z"
  }
}
```
*Note: If `approval_status` or `organization_name` are not set in the database, they will be returned as `null` or default safely without breaking the frontend.*

### 2.4 Refresh Session Token (`POST /auth/refresh`)
Refreshes an expired or expiring access token using the refresh token stored on the client. Returns top-level tokens (`access_token`, `refresh_token`), `message`, `token_type`, `expires_in`, and the `user` object.

- **Endpoint:** `POST /auth/refresh`
- **Auth Required:** No
- **Request Body:**
```json
{
  "refresh_token": "v1.mr..."
}
```
- **Response (200 OK):**
```json
{
  "message": "Token refreshed successfully",
  "access_token": "eyJhbGciOi...new",
  "refresh_token": "v1.mr...new",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "a0000000-0000-0000-0000-000000000001",
    "email": "receiver@example.com"
  }
}
```

---

## 3. Public Food Listing Feed & Details

### 3.1 Public Listings Feed (`GET /listings/`)
Fetches all currently available (`status = 'available'`) listings. Supports pagination, category filtering, and location-based radial queries.

- **Endpoint:** `GET /listings/`
- **Auth Required:** No
- **Query Parameters:**
  | Parameter | Aliases Supported | Type | Default | Description |
  | :--- | :--- | :--- | :--- | :--- |
  | `limit` | - | `integer` | `20` | Max items to return (1-100) |
  | `offset` | - | `integer` | `0` | Offset for pagination |
  | `food_category` | `category` | `string` | `null` | Filter by `human` or `animal` |  
  | `latitude` | `lat` | `float` | `null` | Receiver latitude for radial distance search |
  | `longitude` | `lng` | `float` | `null` | Receiver longitude for radial distance search |
  | `radius_km` | - | `float` | `null` | Search radius in km (Required if `latitude`/`longitude` or their aliases are provided, max 50km) |

- **Example Request:**
```http
GET /listings/?food_category=human&latitude=12.9716&longitude=77.5946&radius_km=10.0&limit=10&offset=0
```

- **Response (200 OK):**
```json
{
  "count": 1,
  "listings": [
    {
      "id": "f0000000-0000-0000-0000-000000000001",
      "title": "Fresh Vegetable Rice",
      "description": "Freshly prepared vegetable rice",
      "food_category": "human",
      "quantity": "5 kg",
      "servings": 20,
      "safe_until": "2026-11-15T18:00:00Z",
      "status": "available",
      "approx_latitude": 12.97,
      "approx_longitude": 77.59,
      "distance_km": 0.25,
      "created_at": "2026-11-14T12:00:00Z"
    }
  ]
}
```

### 3.2 Single Listing Detail (`GET /listings/{id}`)
Fetches public details for a single food listing.
- **Endpoint:** `GET /listings/{id}`
- **Auth Required:** No
- **Response (200 OK):**
```json
{
  "listing": {
    "id": "f0000000-0000-0000-0000-000000000001",
    "title": "Fresh Vegetable Rice",
    "description": "Freshly prepared vegetable rice",
    "food_category": "human",
    "quantity": "5 kg",
    "servings": 20,
    "safe_until": "2026-11-15T18:00:00Z",
    "status": "available",
    "created_at": "2026-11-14T12:00:00Z"
  }
}
```

### 3.3 Strict Privacy Guarantee
To protect donor safety and prevent unauthorized physical drop-ins:
1. Exact coordinates (`latitude`, `longitude`) are **never** returned in `/listings/` or `/listings/{id}`.
2. `pickup_address` and `donor_id` are strictly stripped from all public listing endpoints.
3. The frontend must display map pins using `approx_latitude` and `approx_longitude` (rounded to 2 decimal places, representing a ~1.1 km neighborhood area, e.g., Indiranagar, Koramangala).
4. `distance_km` is computed server-side via the Haversine formula and provided to the frontend for sorting.

---

## 4. Claims Management (Receiver Flow)

### 4.1 Create Claim (`POST /claims/create` or `POST /claims/`)
Claims a food listing. Member 1 supports both `POST /claims/create` (Member 4 preferred) and `POST /claims/`.
- **Endpoint:** `POST /claims/create`
- **Auth Required:** Yes (`role = 'receiver'`)
- **Headers:** `Authorization: Bearer <access_token>`
- **Request Body:**
```json
{
  "listing_id": "f0000000-0000-0000-0000-000000000001"
}
```
- **Response (200 OK):**
```json
{
  "message": "Food listing claimed successfully",
  "claim": {
    "success": true,
    "claim_id": "c0000000-0000-0000-0000-000000000001",
    "listing_id": "f0000000-0000-0000-0000-000000000001",
    "status": "active",
    "expires_at": "2026-11-14T14:45:00Z"
  }
}
```
- **Error Responses:**
  - `400 Bad Request`: `{"detail": "Listing is no longer available"}`
  - `403 Forbidden`: `{"detail": "Only receivers can claim listings"}`
  - `404 Not Found`: `{"detail": "Listing not found"}`

### 4.2 Get My Claims (`GET /claims/my`)
Fetches all claims made by the authenticated receiver, including full pickup details and exact location once claimed.
- **Endpoint:** `GET /claims/my`
- **Auth Required:** Yes (`role = 'receiver'`)
- **Headers:** `Authorization: Bearer <access_token>`
- **Response (200 OK):**
```json
{
  "count": 1,
  "claims": [
    {
      "claim": {
        "id": "c0000000-0000-0000-0000-000000000001",
        "listing_id": "f0000000-0000-0000-0000-000000000001",
        "receiver_id": "a0000000-0000-0000-0000-000000000001",
        "status": "active",
        "expires_at": "2026-11-14T14:45:00Z",
        "created_at": "2026-11-14T14:30:00Z"
      },
      "listing": {
        "id": "f0000000-0000-0000-0000-000000000001",
        "title": "Fresh Vegetable Rice",
        "description": "Freshly prepared vegetable rice",
        "food_category": "human",
        "quantity": "5 kg",
        "servings": 20,
        "safe_until": "2026-11-15T18:00:00Z",
        "status": "claimed",
        "created_at": "2026-11-14T12:00:00Z",
        "pickup_address": "123 Indiranagar 100ft Road, Bengaluru",
        "latitude": 12.9716,
        "longitude": 77.5946
      }
    }
  ]
}
```

### 4.3 Cancel Claim (`POST /claims/{claimId}/cancel`)
Cancels an active claim and restores the listing back to `available`.
- **Endpoint:** `POST /claims/{claimId}/cancel`
- **Auth Required:** Yes (`role = 'receiver'`)
- **Headers:** `Authorization: Bearer <access_token>`
- **Response (200 OK):**
```json
{
  "message": "Claim cancelled successfully",
  "claim_id": "c0000000-0000-0000-0000-000000000001",
  "status": "cancelled"
}
```
- **Error Responses:**
  - `400 Bad Request`: `{"detail": "Cannot cancel completed or expired claim"}`
  - `403 Forbidden`: `{"detail": "You do not have permission to cancel this claim"}`
  - `404 Not Found`: `{"detail": "Claim not found"}`

---

## 5. Frontend Integration Checklist for Member 4

| Step | Action | Endpoint / Config | Expected Result |
| :--- | :--- | :--- | :--- |
| 1 | Configure API Base URL | `http://localhost:8000` | Axios/fetch target |
| 2 | Test OTP Login | `POST /auth/send-otp` $\rightarrow$ `POST /auth/verify-otp` | Store `access_token` and `refresh_token` |
| 3 | Fetch Receiver Profile | `GET /auth/me` | Populate user state in React Context / Redux |
| 4 | Fetch Listings Feed | `GET /listings/?food_category=human&latitude=...&longitude=...&radius_km=10` | Render listing cards and approximate map pins |
| 5 | Verify Coordinate Privacy | Inspect network tab response for `/listings/` | Ensure `pickup_address`, `latitude`, `longitude` are null/absent |
| 6 | Create a Food Claim | `POST /claims/create` with `{ "listing_id": "..." }` | Receive `201 Created` with `claim_id` |
| 7 | View Claim Details | `GET /claims/my` | Displays exact `pickup_address` and `pickup_otp` |
| 8 | Test Claim Cancellation | `POST /claims/{claimId}/cancel` | Claim status changes to `cancelled` |
| 9 | Implement Token Refresh | Interceptor on 401 $\rightarrow$ `POST /auth/refresh` | Seamless token renewal |

---

## 6. Known Dependencies & Boundaries
- **Pickup QR Verification:** Pickup confirmation via QR scanner (`POST /claims/{id}/verify-pickup`) is owned by Member 2 / future sprint. For current receiver flow, `pickup_otp` is provided in `GET /claims/my` for verbal or manual handshake.
- **Impact Dashboard:** Historical impact analytics (kg rescued, CO2 saved) will be connected once Member 2's analytics service lands.
- **Live Supabase Environment:** Backend unit and integration tests have been verified offline using mocked Supabase clients (63 passed, 0 failed, 4 skipped in offline testing; no live Supabase integration claimed). Live Supabase integration, database RLS policies, and staging deployment must be verified using dedicated non-production Supabase infrastructure.
