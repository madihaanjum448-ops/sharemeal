
from typing import Any, Dict

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth_client import auth_supabase
from app.core.supabase_client import get_supabase

security = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:

    try:
        response = auth_supabase.auth.get_user(credentials.credentials)
        user = response.user
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
        )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
        )

    try:
        result = (
            get_supabase()
            .table("user_profiles")
            .select("id, role, is_verified, approval_status")
            .eq("id", user.id)
            .limit(1)
            .execute()
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Profile service temporarily unavailable",
        )

    profile = (result.data or [None])[0]

    if not profile:
        raise HTTPException(
            status_code=403,
            detail="User profile not found",
        )

    return {
        "id": user.id,
        "role": profile["role"],
        "is_verified": bool(profile.get("is_verified", False)),
        "approval_status": profile.get("approval_status"),
    }


def get_current_donor(user=Depends(get_current_user)):
    if user["role"] != "donor":
        raise HTTPException(
            status_code=403,
            detail="Only donors can perform this operation",
        )
    return user


def get_current_verified_receiver(user=Depends(get_current_user)):
    if user["role"] != "receiver":
        raise HTTPException(
            status_code=403,
            detail="Only recipient organisations can access this feature",
        )

    if user["approval_status"] != "approved" or not user["is_verified"]:
        raise HTTPException(
            status_code=403,
            detail="Receiver account requires administrator approval",
        )

    return user


def get_current_admin(user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Administrator access required",
        )
    return user
