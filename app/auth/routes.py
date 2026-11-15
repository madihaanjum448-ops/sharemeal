
import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.schemas import SendOTPRequest, VerifyOTPRequest, RefreshTokenRequest
from app.core.auth import get_current_user
from app.core.auth_client import auth_supabase
from app.core.config import settings
from app.core.rate_limit import enforce_otp_send_limit
from app.core.supabase_client import get_supabase

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger("sharemeal.auth")


@router.post("/send-otp")
def send_otp(request: SendOTPRequest, http_request: Request):
    email = request.email.strip().lower()
    ip = http_request.client.host if http_request.client else "unknown"

    enforce_otp_send_limit(
        f"{ip}:{email}",
        settings.OTP_MAX_SENDS_PER_WINDOW,
        settings.OTP_RATE_LIMIT_WINDOW_SECONDS,
    )

    try:
        auth_supabase.auth.sign_in_with_otp({
            "email": email,
            "options": {"should_create_user": True},
        })
        return {"message": "Verification code sent. Please check your email."}

    except Exception as exc:
        logger.exception(
            "Supabase OTP delivery failed: %s",
            type(exc).__name__,
            )
        raise HTTPException(
            status_code=503,
            detail="Could not send verification code. Please try again later."
            )


@router.post("/verify-otp")
def verify_otp(request: VerifyOTPRequest, http_request: Request):
    email = request.email.strip().lower()
    ip = http_request.client.host if http_request.client else "unknown"

    enforce_otp_send_limit(
        f"verify:{ip}:{email}",
        5,
        settings.OTP_RATE_LIMIT_WINDOW_SECONDS,
    )

    try:
        verification = auth_supabase.auth.verify_otp({
            "email": email,
            "token": request.token,
            "type": "email",
        })

        user, session = verification.user, verification.session

        if not user or not session:
            raise HTTPException(
                status_code=401,
                detail="OTP verification failed",
            )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Supabase OTP verification failed: %s",
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=401,
            detail="OTP verification failed",
        )

    try:
        client = get_supabase()

        existing = (
            client.table("user_profiles")
            .select(
                "id, full_name, role, organization_name, "
                "is_verified, approval_status"
            )
            .eq("id", user.id)
            .limit(1)
            .execute()
        )

        if existing.data:
            profile = existing.data[0]

        else:
            if not request.full_name or not request.role:
                raise HTTPException(
                    status_code=422,
                    detail="full_name and role are required for a new profile",
                )

            role = request.role

            payload = {
                "id": user.id,
                "full_name": request.full_name.strip(),
                "role": role,
                "organization_name": (
                    request.organization_name.strip()
                    if request.organization_name
                    else None
                ),
                "approval_status": (
                    "pending" if role == "receiver" else None
                ),
            }

            created = (
                client.table("user_profiles")
                .insert(payload)
                .execute()
            )

            if not created.data:
                raise HTTPException(
                    status_code=500,
                    detail="Profile creation failed",
                )

            profile = created.data[0]

        return {
            "message": "Email verified and login successful.",
            "user": {
                "id": user.id,
                "email": user.email,
            },
            "profile": profile,
            "session": {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "token_type": session.token_type,
                "expires_in": session.expires_in,
            },
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception("User profile lookup or creation failed")
        raise HTTPException(
            status_code=500,
            detail="Account setup failed. Please try again later.",
        )


@router.get("/me")
def get_current_user_profile(user=Depends(get_current_user)):
    """Return the authenticated user's profile information."""
    try:
        client = get_supabase()
        res = (
            client.table("user_profiles")
            .select(
                "id, full_name, phone, role, organization_name, "
                "is_verified, approval_status, created_at"
            )
            .eq("id", user["id"])
            .limit(1)
            .execute()
        )
        if not res.data:
            raise HTTPException(
                status_code=404,
                detail="User profile not found",
            )
        profile = res.data[0]
        email = user.get("email")

        user_data = {
            "id": profile["id"],
            "email": email,
            "full_name": profile["full_name"],
            "role": profile["role"],
            "organization_name": profile.get("organization_name"),
            "is_verified": bool(profile.get("is_verified", False)),
            "approval_status": profile.get("approval_status"),
            "created_at": profile.get("created_at"),
        }
        return {
            **user_data,
            "user": user_data,
            "profile": user_data,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to retrieve user profile: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve user profile",
        )


@router.post("/refresh")
def refresh_token(request: RefreshTokenRequest):
    """Refresh Supabase session using an existing refresh token."""
    try:
        token = request.refresh_token.strip()
        refresh_res = auth_supabase.auth.refresh_session(token)
        session = getattr(refresh_res, "session", None)
        user = getattr(refresh_res, "user", None)

        if not session:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired refresh token",
            )

        return {
            "message": "Token refreshed successfully",
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "token_type": getattr(session, "token_type", "bearer"),
            "expires_in": getattr(session, "expires_in", 3600),
            "user": {
                "id": user.id if user else None,
                "email": getattr(user, "email", None),
                },
                }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Token refresh failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token",
        )
